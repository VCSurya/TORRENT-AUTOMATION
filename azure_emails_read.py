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
from main import process_pdf
from dotenv import load_dotenv
import time
import copy
from PIL import Image
from pypdf import PdfReader

load_dotenv()
# =============================
#  CONFIGURATION (UPDATE SECRET)
# =============================
 
EMAIL_LOGS = []
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
SCOPES = [f"{os.getenv("SCOPES_URL")}"]
USER_ID = os.getenv("USER_ID")

# =============================
#  AUTHENTICATE CLIENT
# =============================
 
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

    """
    Returns:
      digital_signed: True if cryptographic signature exists (/Sig)
      has_stamp: True if Stamp annotation exists (/Stamp) -> visual only
    """
    reader = PdfReader(pdf_path)

    digital_signed = False
    has_stamp = False

    # 1) Check AcroForm fields if present (real digital signature fields)
    root = reader.trailer["/Root"]
    acroform = root.get("/AcroForm")
    if acroform:
        fields = acroform.get("/Fields", [])
        for fld_ref in fields:
            fld = fld_ref.get_object()
            if fld.get("/FT") == "/Sig":
                v = fld.get("/V")
                if v:
                    sig = v.get_object()
                    if "/ByteRange" in sig and "/Contents" in sig:
                        digital_signed = True
                        break
                # Signature field exists even if value not resolved
                digital_signed = True
                break

    # 2) Scan page annotations (/Annots)
    for page in reader.pages:
        annots = page.get("/Annots", [])
        for a in annots:
            annot = a.get_object()
            subtype = annot.get("/Subtype")

            # (A) Visual stamp detection (NOT a digital signature)
            if subtype == "/Stamp":
                has_stamp = True

            # (B) Real digital signature widget
            if subtype == "/Widget" and annot.get("/FT") == "/Sig":
                v = annot.get("/V")
                if v:
                    sig = v.get_object()
                    if "/ByteRange" in sig and "/Contents" in sig:
                        digital_signed = True
                else:
                    digital_signed = True

        # early exit if you want faster performance
        if digital_signed and has_stamp:
            break

    if digital_signed:
        return True
    
    else:   
        try:
            with open(pdf_path, "rb") as f:
                r = PdfFileReader(f)
                return len(r.embedded_signatures) > 0
        except Exception:
            
            if has_stamp:
                return True
            return False



# =============================
#  FETCH MESSAGES (PAGING)
# =============================
async def fetch_messages_with_filter(threshold_iso: str, max_count: int = 100):
 
    print(f"\nFetching messages received after: {threshold_iso}")
 
    query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
        filter=f"receivedDateTime ge {threshold_iso}",
        expand=["attachments"],
        top=50
    )
 
    request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
 
    request_builder = (
        graph_client.users
        .by_user_id(USER_ID)
        .mail_folders
        .by_mail_folder_id("Inbox")
        .messages
    )
 
    all_messages = []
 
    # First page
    response = await request_builder.get(request_configuration=request_config)
 
    # Paging loop — FIXED
    while True:
        all_messages.extend(response.value)
 
        if not response.odata_next_link:
            break
 
        # Continue using nextLink exactly — DO NOT hardcode folder names
        response = await graph_client \
            .users.by_user_id(USER_ID) \
            .messages.with_url(response.odata_next_link) \
            .get()
 
    print(f"Total messages found (before limit): {len(all_messages)}")
 
    # Sort locally
    all_messages.sort(key=lambda m: m.received_date_time)
 
    return all_messages[:max_count]
 
# =============================
#  MAIN FUNCTION
# =============================
async def process_filtered_emails(shared_data):
 
    try:

        start_time = time.time()

        bot_opration = {
            "start_time": {str(datetime.now())},
            "emails":[]
        }

        shared_data["status"].append(f"3. Start Process - {str(datetime.now())}")
        


        with open("latest/latest_proceed_email.json", "r") as file:
            data = json.load(file)

        # ============
        # SET THRESHOLD
        # ============
        # threshold_dt = datetime.fromisoformat("2025-11-27 09:11:38+00:00")
        threshold_dt = datetime.fromisoformat(data.get("email_date_time"))
        last_visited_email_id = data.get("id")
 
        # convert to UTC "Z" format
        threshold_iso = threshold_dt.isoformat().replace("+00:00", "Z")


        shared_data["status"].append(f"4. Reading New Emails From Cloude...")

        # =============
        # FETCH MESSAGES
        # =============
        messages = await fetch_messages_with_filter(
            threshold_iso=threshold_iso,
            max_count=300
        )
 
        if not messages:
            EMAIL_LOGS.append("25: No new messages found.")
            return
        
        shared_data["status"].append(f"5. {len(messages)} - Emails Found")
        email_no = 1
 
        # ==========================
        # PROCESS EACH MESSAGE SAFELY
        # ==========================
        
        for message in messages:

            shared_data["status"].append(f">> {email_no} - Email Processing...")
            shared_data["status"].append(f">> Subject: {message.subject} ")
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
                                if file_name.endswith(".pdf") or file_name.endswith(".PDF"):
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
                        "result": []
                    }

                    
                    error = 0
                    success = 0
                    total = len(os.listdir(temp_dir))
                    latest_opration_data['Total Proceed Pdf'] = email_data["Total Proceed Pdf"] =  str(total)
                    latest_opration_data['Success Proceed Pdf'] = email_data['Success Proceed Pdf'] = str(success)
                    latest_opration_data['Error Proceed Pdf'] = email_data['Error Proceed Pdf'] = str(error)
                    
                    shared_data["proceed_emails"][f"{str(message.id)}"] = latest_opration_data
                    shared_data["last_visited_email_detailes"] = latest_opration_data 
                    update_json_file("latest/latest_proceed_email.json", copy.deepcopy(latest_opration_data))



                    if len(os.listdir(temp_dir)) > 0:


                        shared_data["status"].append(f">> {len(os.listdir(temp_dir))} Digital Signed Attachment Found!")
                        shared_data["status"].append(f">> Attachments Processing...")
                        
                        
                        
                        shared_data["proceed_emails"][str(message.id)] = latest_opration_data
                        shared_data["last_visited_email_detailes"] = latest_opration_data 
                        update_json_file("latest/latest_proceed_email.json", copy.deepcopy(latest_opration_data)) 

                        for filename in os.listdir(temp_dir):
                            shared_data["status"].append(f">> ({filename}) Processing...")
                            pdf_file_path = os.path.join(temp_dir,filename)
                            response = process_pdf(pdf_file_path,email_data)
                            
                            if response['status']:

                                if response['json']['ErrorType'] == "S":
                                    success += 1
                                    latest_opration_data['Success Proceed Pdf'] = email_data['Success Proceed Pdf'] = str(success)
                                    
                                else:
                                    shared_data["status"].append(f"ERROR({response['json']['ErrorMsg']}): {response['json']['ErrorNo']}")
                                    error += 1
                                    latest_opration_data['Error Proceed Pdf'] = email_data['Error Proceed Pdf'] = str(error)

                                response.pop("json")
                                latest_opration_data['result'].append(response)

                            else:
                                
                                shared_data["status"].append(f"ERROR({response['json']['ErrorMsg']}): {response['json']['ErrorNo']}")
                                latest_opration_data['result'].append(response)
                                error += 1
                                latest_opration_data['Error Proceed Pdf'] = email_data['Error Proceed Pdf'] = str(error)

                            shared_data["proceed_emails"][str(message.id)] = latest_opration_data
                            shared_data["last_visited_email_detailes"] = latest_opration_data 
                            update_json_file("latest/latest_proceed_email.json", copy.deepcopy(latest_opration_data)) 
                            shared_data["status"].append(f">> ({filename}) Proceed!")


                    else:
                        shared_data["status"].append(f">> No Digital Signed Attachment Found!")
                     
                    shared_data["status"].append(f">> {email_no} - Email Proceed.")
                    # latest_opration_data.pop("id")

                    shared_data["proceed_emails"][str(message.id)] = latest_opration_data
                    # bot_opration["emails"].append(latest_opration_data)
                
                # shared_data["proceed_emails"] = bot_opration["emails"]
                # shared_data["proceed_emails"][str(message.id)] = latest_opration_data

            else:
                shared_data["status"].append(">> !!! Email Already Proceed.")
                shared_data["status"].append(f">> {email_no} - Email Proceed.")
            
            email_no = email_no +  1    


        shared_data["status"].append(f"6. ALL Emails Procced Successfully.")


    except ODataError as odata_error:
        EMAIL_LOGS.append(f"129: {odata_error.error.code} - {odata_error.error.message}")
        shared_data["status"].append(f"*Exception Error* 129: {odata_error.error.code} - {odata_error.error.message}")
        

    except:
        import traceback
        e =  traceback.format_exc()
        EMAIL_LOGS.append(f"128: {str(e)}")
        shared_data["status"].append(f"*Exception Error* 128: {str(e)}")

    finally:
        pass

# # =============================
# #  ENTRY POINT
# # =============================
# if __name__ == "__main__":
#     asyncio.run(process_filtered_emails())
 
 