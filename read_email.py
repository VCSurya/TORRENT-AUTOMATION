import asyncio
import os
import base64
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
import tempfile
import zipfile
from datetime import datetime
import json
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.pdf_utils.reader import PdfFileReader
from main import process_pdfs
from dotenv import load_dotenv
import time
import copy
from PIL import Image

load_dotenv()

EMAIL_LOGS = []
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
SCOPES = [f"{os.getenv("SCOPES_URL")}"]
USER_ID = os.getenv("USER_ID")

# Authenticate using client credentials
credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

graph_client = GraphServiceClient(credential, scopes=SCOPES)


async def get_folder_names():
    folders_response = await graph_client.users.by_user_id(USER_ID).mail_folders.get()
    print(folders_response)
    folder_names = [folder.display_name for folder in folders_response.value]
    for folder_name in folder_names:
        print(folder_name)

def is_image(filename: str) -> bool:
    ext = filename.lower().split(".")[-1]
    return True if ext in os.getenv("IMAGE_EXTS") else False

def update_json_file(file_path: str, new_data: dict) -> bool:
    try:
        
        new_data.pop("result")
        new_data.pop("attchments")

        with open(file_path, "w") as file:
            json.dump(new_data, file, indent=4)

        return True
    except Exception as e:
        # print(f"126 {str(e)}")
        return False


def verify_signatures(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            reader = PdfFileReader(f)
            sig_fields = list(enumerate_sig_fields(reader))
            return bool(sig_fields)
    except:
        return False


async def get_emails_and_download_attachments(shared_data):

    

    try:
        load_dotenv(override=True)
        start_time = time.time()

        bot_opration = {
            "start_time": str(datetime.now()),
            "emails":[]
        }

        shared_data["status"].append(f"3. Start Process - {bot_opration["start_time"]}")
        shared_data["proceed_emails"] = bot_opration["emails"]
        
        messages_request_builder = (
            graph_client.users
            .by_user_id(USER_ID)
            .mail_folders
            .by_mail_folder_id("AQMkADZkNTE1NjRmLTBhMmUtNGYxMi1hMzA3LTJlZDRhNTc2MDg2NAAuAAAD42_v49cfGEqBW867VJ8guwEAys2jAdFql0C_OQH-YLOULAAAAgEMAAAA") # Inbox Folder
            # .by_mail_folder_id("AAMkADJlNDU0NDFhLTVhMTUtNDUxYy1hODM5LWJhM2FlM2QxNzY2NQAuAAAAAAC9s70Y2dotQrZCAtEZylaNAQCxhD1TlNm_T5GU2HoWBeCoAANDbCisAAA=") # Action Tacken Folder
            .messages
        )

        with open("latest/latest_proceed_email.json", "r") as file:
            data = json.load(file)

        threshold_time = data.get("email_date_time")
        last_visited_email_id = data.get("id")

        threshold_iso = datetime.fromisoformat(threshold_time).isoformat().replace("+00:00", "Z")

        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            filter=f"receivedDateTime ge {threshold_iso}",
            expand=["attachments"],
            top=50
        )

        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        shared_data["status"].append(f"4. Reading New Emails From Cloude...")
        messages_result = []
        
        response = await messages_request_builder.get(request_configuration=request_config)

        # Paging loop — FIXED
        while True:
            messages_result.extend(response.value)
    
            if not response.odata_next_link:
                break
    
            # Continue using nextLink exactly — DO NOT hardcode folder names
            response = await graph_client \
                .users.by_user_id(USER_ID) \
                .messages.with_url(response.odata_next_link) \
                .get()
    
        messages_result.sort(key=lambda m: m.received_date_time)

        # if not messages_result or not messages_result or len(messages_result) == 0:
        #     EMAIL_LOGS.append("25: No new messages found.")
        
        # if last_visited_email_id[:12] == "HARE_KRISHNA":
        #     shared_data["status"].append(f"5. {len(messages_result) if len(messages_result)!=0 else 0} - Emails Found")
        # else:
        #     shared_data["status"].append(f"5. {len(messages_result) if len(messages_result)!=0 else 0} - Emails Found")

        shared_data["status"].append(f"5. {len(messages_result)} - Emails Found")
        email_no = 1

        for message in messages_result:

            shared_data["status"].append(f"> {email_no} - Email Processing...")
            if message.id != last_visited_email_id:
                email_data = {
                        "vandor_email":str(message.sender.email_address.address),
                        "email_date_time":str(message.received_date_time),
                        "email_subject":str(message.subject)
                }

                all_attchments_name = {"pdfs": []}
                with tempfile.TemporaryDirectory(dir=os.path.join(os.getcwd(), 'temp')) as temp_dir:
                    if message.has_attachments and message.attachments:
                        for attachment in message.attachments:
                            if attachment.odata_type == "#microsoft.graph.fileAttachment":
                                file_content = base64.b64decode(attachment.content_bytes)
                                file_name = attachment.name

                                # PDF file handling
                                if file_name.endswith(".pdf"):
                                    file_path = os.path.join(temp_dir, file_name)
                                    with open(file_path, "wb") as f:
                                        f.write(file_content)

                                    if verify_signatures(file_path):
                                        all_attchments_name["pdfs"].append(
                                            {"filename": file_name, "Digital Sign": True})
                                    else:
                                        all_attchments_name["pdfs"].append(
                                            {"filename": file_name, "Digital Sign": False})
                                        os.remove(file_path)

                                # ZIP file handling
                                elif file_name.endswith(".zip"):
                                    all_attchments_name[file_name] = []
                                    zip_file_path = os.path.join(temp_dir, file_name)

                                    with open(zip_file_path, "wb") as f:
                                        f.write(file_content)

                                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                                        zip_ref.extractall(temp_dir)
                                        for extracted_file in zip_ref.namelist():
                                            if extracted_file.endswith(".pdf"):
                                                file_path = os.path.join(temp_dir, extracted_file)
                                                if verify_signatures(file_path):
                                                    all_attchments_name[file_name].append(
                                                        {"filename": extracted_file, "Digital Sign": True})
                                                else:
                                                    all_attchments_name[file_name].append(
                                                        {"filename": extracted_file, "Digital Sign": False})
                                                    os.remove(file_path)
                                    os.remove(zip_file_path)
                                
                                ## Image file handling
                                # elif is_image(file_name) :
                                #     ext = file_name.lower().split(".")[-1]

                                #     file_path = os.path.join(temp_dir, file_name)

                                #     with open(file_path, "wb") as f:
                                #         f.write(file_content)

                                #     img = Image.open(file_path)
                                #     img = img.convert("RGB")
                                #     pdf_path = file_path.replace(ext,"pdf")
                                #     img.save(pdf_path)
                                #     all_attchments_name["pdfs"].append({"filename": file_name.replace(ext,"pdf"), "Digital Sign": "It's Image"})
                                    
                    
                    latest_opration_data = {
                        "id": str(message.id),
                        "from": str(message.sender.email_address.address),
                        "subject": str(message.subject),
                        "email_date_time": str(message.received_date_time),
                        "process_date_time": str(datetime.now()),
                        "attchments":all_attchments_name,
                        "result": None
                    }

                    if len(os.listdir(temp_dir)) > 0:
                        response = process_pdfs(temp_dir,email_data)
                        if response['status']:
                            
                            # if not response['result']['status']:
                            latest_opration_data['result'] = response['result']
                            
                            error = 0
                            success = 0
                            total = len(latest_opration_data['result'])

                            for i in latest_opration_data['result']:
                                print(i)
                                if not i['status']:
                                    shared_data["status"].append(f"ERROR({i['json']['ErrorMsg']}): {i['json']['ErrorNo']}")

                                if i['json']['ErrorType'] == "S":
                                    success += 1
                                else:
                                    error += 1
                                
                            latest_opration_data['Total Proceed Pdf'] = email_data["Total Proceed Pdf"] =  str(total)
                            latest_opration_data['Error Proceed Pdf'] = email_data['Error Proceed Pdf'] = str(error)
                            latest_opration_data['Success Proceed Pdf'] = email_data['Success Proceed Pdf'] = str(success)
                            
                        else:
                            latest_opration_data['result'] = response['error']
                    
                    shared_data["last_visited_email_detailes"] = latest_opration_data 
                    update_json_file("latest/latest_proceed_email.json", copy.deepcopy(latest_opration_data))         
                    
                    shared_data["status"].append(f"> {email_no} - Email Proceed.")
                    latest_opration_data.pop("id")

                    try:
                        for x in latest_opration_data['result']:
                            if x['status']:
                                x.pop("json")
                    except:
                        pass 
                    bot_opration["emails"].append(latest_opration_data)
                
                shared_data["proceed_emails"] = bot_opration["emails"]
                email_no = email_no +  1    
                
                time.sleep(1)
            
            else:
                shared_data["status"].append("!!! Email Already Proceed.")
                shared_data["status"].append(f"> {email_no} - Email Proceed.")
                email_no = email_no +  1

        shared_data["status"].append(f"6. ALL Emails Procced Successfully.")

    except ODataError as odata_error:
        EMAIL_LOGS.append(f"129: {odata_error.error.code} - {odata_error.error.message}")
        shared_data["status"].append(f"*Exception Error* 129: {odata_error.error.code} - {odata_error.error.message}")
        

    except:
        import traceback
        e = traceback.format_exc()
        EMAIL_LOGS.append(f"128: {str(e)}")
        shared_data["status"].append(f"*Exception Error* 128: {str(e)}")

    finally:
        # Record the execution time
        end_time = time.time()
        execution_time = end_time - start_time
        # Update bot operation data
        bot_opration['end_time'] = str(datetime.now())
        bot_opration['duration'] = str(execution_time)
        bot_opration['logs'] = EMAIL_LOGS
        shared_data["proceed_emails"] = bot_opration["emails"]


# if __name__ == "__main__":

#     shared_data = {
#         "status":[]
#     }

#     asyncio.run(get_emails_and_download_attachments(shared_data))
#     # asyncio.run(get_folder_names()) # using this method you can get the all folder names of email like inbox, draft , trash bin etc.
