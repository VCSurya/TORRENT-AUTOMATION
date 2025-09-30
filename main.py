import os
import re
import fitz
import json
import time
import base64
import random
import requests
import concurrent.futures
from dotenv import load_dotenv
from openai import AzureOpenAI
from itertools import combinations
from difflib import SequenceMatcher,get_close_matches
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

load_dotenv()

LOGS = []
# Get the directory where the current script is located
SCRTPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- SAP URLs ---
BASE_URL = os.getenv('SAP_BASE_URL')
POST_URL = f"{BASE_URL}/ZFI_DCC_HEADERSet"
ATTACHMENT_URL = f"{BASE_URL}/AttachmentSet"
# For CSRF token fetch, root or entityset is enough (no $expand needed)
TOKEN_URL = f"{BASE_URL}/"

# --- SAP Credentials ---
SAP_USERNAME = os.getenv('SAP_USERNAME')   
SAP_PASSWORD = os.getenv('SAP_PASSWORD')   

### >>> Load the SAP JSON Tamplate
SAP_JSON = None
sap_file_path = os.path.join(SCRTPT_DIR, 'sap.json')
with open(sap_file_path, 'r') as file:
    SAP_JSON = json.load(file)



### >>> Load the PAN Numbers From TXT File
PAN_NO = None
prompt_path  = os.path.join(SCRTPT_DIR, 'pan.txt')
with open(prompt_path, 'r') as file:
    PAN_NO = set(file.read().splitlines())

# Extracting The File Name From SAP PDF POST API Response
def extract_file_name(xml_text):
    start_tag = "<d:FileName>"
    end_tag = "</d:FileName>"

    start_index = xml_text.find(start_tag)
    if start_index == -1:
        return None  # FileName tag not found

    start_index += len(start_tag)
    end_index = xml_text.find(end_tag, start_index)
    if end_index == -1:
        return None  # Closing tag not found

    return xml_text[start_index:end_index]


# === Retry decorator ===
def retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(Exception,)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = 1
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if attempt == max_retries - 1:
                        LOGS.append(f"Failed after {max_retries} retries: {e}")
                        raise
                    sleep_time = delay + random.uniform(0, 0.5)  # jitter
                    LOGS.append(f"Error: {e} → retrying in {sleep_time:.1f}s (attempt {attempt+1})")
                    time.sleep(sleep_time)
                    delay *= backoff_factor
        return wrapper
    return decorator

# === Step 1: Extract text from Azure ===
@retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
def azure_extract_text(pdf_file):
    
        LOGS.append(f"4")
        try:

            endpoint = os.getenv("AZURE_ENDPOINT")
            key = os.getenv("AZURE_API_KEY")
            # Create client
            client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

            # Open PDF and send to Azure
            with open(pdf_file, "rb") as f:
                poller = client.begin_analyze_document(
                    model_id="prebuilt-read",
                    body=f
                )

            result = poller.result()

            # Extract all text
            text = []
            for page in result.pages:
                for line in page.lines:
                    text.append(line.content)


            if len(text) > 0:
                TEXT = "\n".join(text)
                LOGS.append(f'5')
                doc = fitz.open(pdf_file)
                extracted_words = {}

                for page in result.pages:  # Azure page object
                    # Get the matching PyMuPDF page by index (Azure is 1-based, PyMuPDF is 0-based)
                    pymupdf_page = doc[page.page_number - 1]
                    page_width = pymupdf_page.rect.width
                    page_height = pymupdf_page.rect.height

                    for word in page.words:
                        bbox = word.polygon  # list of floats [x1, y1, ..., x4, y4]

                        xs = bbox[0::2]  # even indices = x values
                        ys = bbox[1::2]  # odd indices = y values

                        x = min(xs)
                        y = min(ys)
                        width = max(xs) - x
                        height = max(ys) - y

                        key = word.content
                        value = [page.page_number, x, y, width, height, page_width, page_height]

                        if key not in extracted_words:
                            extracted_words[key] = []
                        extracted_words[key].append(value)
                
                LOGS.append(f"6")
                LOGS.append(f"7")

                with open('latest/latest_pdf_azure_text.txt', 'w',encoding='utf-8') as file:
                    file.write(TEXT)

                return {'status':True,'text':TEXT,'cordinates':extracted_words}

            else:
                LOGS.append(f"104") 
                return {'status':False,'error':"Text Not Extracted From AZURE"}

        except Exception as e:
            LOGS.append(f"103 {str(e)}")
            return {'status':False,'error':str(e)}

# === Step 2: Send to LLM ===
@retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
def format_with_llm(text):

    try:
        # Environment variables
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")     # e.g. https://my-resource.openai.azure.com/
        key = os.getenv("AZURE_OPENAI_KEY")               # API key from Azure portal
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") # Deployment name in Azure (e.g. gpt-4.1-mini)

        # Create Azure OpenAI client
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )
        
        ### >>> Load the Prompt Tamplate From TXT File
        propmt = ""
        prompt_path  = os.path.join(SCRTPT_DIR, 'prompt.txt')
        with open(prompt_path, 'r') as file:
            propmt = file.read()

        propmt = propmt + '\n' + text

        # Call GPT-4.1-mini with forced JSON output
        response = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},  # 👈 Force valid JSON
            messages=[
                {
                    "role": "system",
                    "content": "You are a data extraction assistant. Always respond strictly in JSON format only."
                },
                {
                    "role": "user",
                    "content": propmt
                }
            ],
            max_tokens=1500,
            temperature=0
        )

        with open('latest/latest_pdf_open_ai_respons.txt', 'w',encoding='utf-8') as file:
            file.write(str(response))

        LOGS.append(f"9")
        content = response.choices[0].message.content
        parsed_data = json.loads(content)  # convert JSON string to dict
        LOGS.append(f"10 \n\n{parsed_data}")
        return {'status':True,'json':parsed_data}

    except Exception as e:
        LOGS.append(f'105 {str(e)}')
        return {'status':False,'error':str(e)}

def final_json(JSON):
    
    try:

        def gst_validations(gst_list):
            
            def similarity(a, b):
                return SequenceMatcher(None, a, b).ratio()
            
            try:    
                best_gst = None
                best_score = -1
                
                for gst in gst_list:
                    gst_pan_part = gst[2:12]  # GST PAN is at position 3-12
                    for pan in PAN_NO:
                        score = similarity(gst_pan_part, pan)
                        if score > best_score:
                            best_score = score
                            best_gst = gst
                
                gst_list.remove(best_gst)
                vendor_gst = gst_list[0] if len(gst_list) > 0 else "" 
                
                return {'status':True , "CompanyGstinPdf":best_gst,"VendorGstin":vendor_gst}
            
            except Exception as e:
                return {'status':False , "error":str(e)}

        def get_irn_number(lst):

            try:
                """
                Takes a list of strings and returns the first string of exactly 64 characters.
                - If any item itself is 64 chars → return it directly.
                - Otherwise, try all possible combinations of items in sequence order.
                - If no such string exists → return empty string.
                """
                # 1️⃣ Direct check: any single item of length 64
                for item in lst:
                    if len(item) == 64:
                        return item

                n = len(lst)
                # 2️⃣ Try all possible combinations
                for r in range(2, n+1):  # size of combination
                    for indices in combinations(range(n), r):
                        merged = "".join(lst[i] for i in indices)
                        if len(merged) == 64:
                            return merged
                
                # 3️⃣ No solution
                return ""

            except Exception as e:
                LOGS.append(f'108 {str(e)}')

        def get_closest_10_digit_string(text, input_string):

            # Initialize variables to store the best match and its similarity
            best_match = None
            highest_similarity = 0
            
            try:
                # Extract all 10-digit substrings using regular expressions
                potential_matches = re.findall(r'\d{10}', text)

                if not potential_matches:
                    return None, 0  # If no 10-digit numbers are found
                
                # Function to calculate similarity using SequenceMatcher
                def calculate_similarity(str1, str2):
                    return SequenceMatcher(None, str1, str2).ratio()

                # Compare each 10-digit substring with the input string
                for match in potential_matches:
                    similarity = calculate_similarity(input_string, match)
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = match

                return best_match
            
            except Exception as e:
                LOGS.append(f'109 {str(e)}')
                return best_match
                
        def convert_normalized_to_absolute(cordinates):
            try:
                x0 = cordinates[1] * 72
                y0 = cordinates[2] * 72
                x1 = x0 + cordinates[3] * 72
                y1 = y0 + cordinates[4] * 72
                return f"{cordinates[0]},{x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}"
            except:
                LOGS.append(f'110 {str(e)}')
                return f"{cordinates[0]},{cordinates[1]},{cordinates[2]},{cordinates[3]},{cordinates[4]}"

        def find_closest(data: dict, target: str) -> str:

            keys = list(data.keys())
            # First, check exact substring match
            substring_matches = [k for k in keys if str(target) in k]

            if substring_matches:
                matched_key = substring_matches[0]  # pick first substring match
            else:
                # Try get_close_matches
                matches = get_close_matches(str(target), keys, n=1, cutoff=0.6)
                if matches:
                    matched_key = matches[0]
                else:
                    # fallback to absolute closest using ratio
                    matched_key = max(keys, key=lambda k: SequenceMatcher(None, str(target), k).ratio())

            # Prepare structured coordinates
            coords_list = []
            for coord in data[matched_key]:
                if len(coord) == 7:  # expected 7 elements
                    coords_list.append({
                        'page': coord[0],
                        'x': coord[1],
                        'y': coord[2],
                        'width': coord[3],
                        'height': coord[4],
                        'page_width': coord[5],
                        'page_height': coord[6]
                    })
                else:
                    coords_list.append({'raw': coord})  # fallback if malformed

            return matched_key
                
        with open('latest/latest_pdf_azure_text_cordinates.txt', 'w',encoding='utf-8') as file:
            file.write(str(JSON['cordinates']))

        gst_result = gst_validations(JSON['data']['Gst'])

        if gst_result['status']:
            SAP_JSON['CompanyGstinPdf'] = gst_result['CompanyGstinPdf']
            SAP_JSON['VendorGstin'] = gst_result['VendorGstin']
        else:
            LOGS.append(f'107 {gst_result}')

        SAP_JSON['IrnNo'] = JSON['data']['IrnNo'] 
        if len(JSON['data']['IrnNo']) != 64:
            pattern = r'\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*[0-9])[0-9a-fA-F]{10,64}\b'
            matches = re.findall(pattern, JSON['text']) # Find all matches
            res = get_irn_number(matches)
            if res != "":
                SAP_JSON['IrnNo'] = res

        total_scs_no = []

        for index, data in enumerate(set(JSON['data']['SesGrn'])):
            
            ses_no = data

            # Check if data is not exactly 10-digit numeric
            if not (len(data) == 10 and data.isdigit()):
                closest_string = get_closest_10_digit_string(JSON['text'], data)
                if closest_string:
                    ses_no = closest_string  # replace with closest match
            
            if ses_no not in total_scs_no:
                
                SAP_JSON['DCCHEADERTODCCSES'].append(
                    {
                        "InwardRefNo": "",
                        "PoNo": "",
                        "SesGrnScrollNoPdf": ses_no,
                        "ItemNo": f"{index+1}",
                        "SesGrnScrollNoSap": "",
                        "ParkDocNo": "",
                        "Amount": f"{JSON['data']['InvoiceAmount']}",
                        "CreatedOn": "",
                        "Zindicator": "",
                        "CreatedBy": "",
                        "CSesGrnScrollNoPdf": "",
                        "ChangedOn": "",
                        "ChangedBy": ""
                    }
                )

                total_scs_no.append(ses_no)

        SAP_JSON['InvoiceNo'] = JSON['data']['InvoiceNo']
        SAP_JSON['InvoiceDate'] = JSON['data']['InvoiceDate'].replace("-","")
        SAP_JSON['InvoiceAmount'] = JSON['data']['InvoiceAmount']
        SAP_JSON['PoLpoIoNoPdf'] = JSON['data']['PoNo'].split('/')[-1]
        # SAP_JSON['CPoLpoIoNo'] = JSON['data']['Email Id']

        if SAP_JSON['CompanyGstinPdf'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['CompanyGstinPdf']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CCompanyGstinPdf"] = result
        
        if SAP_JSON['VendorGstin'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['VendorGstin']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CVendorGstin"] = result

        if SAP_JSON['InvoiceNo'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['InvoiceNo']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CInvoiceNo"] = result

        if SAP_JSON['InvoiceDate'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['InvoiceDate']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CInvoiceDate"] = result

        if SAP_JSON['InvoiceAmount'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['InvoiceAmount']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CInvoiceAmount"] = result

        if SAP_JSON['PoLpoIoNoPdf'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['PoLpoIoNoPdf']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CPoLpoIoNo"] = result

        if SAP_JSON['IrnNo'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['IrnNo']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CIrnNo"] = result

        for item in SAP_JSON['DCCHEADERTODCCSES']:
            ses_grn_scroll_no_pdf = item['SesGrnScrollNoPdf']

            closest_key = find_closest(JSON['cordinates'], str(ses_grn_scroll_no_pdf))
            # Assuming `convert_normalized_to_absolute` is a function defined elsewhere
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])        
            # Here we update the item directly in the list
            item["CSesGrnScrollNoPdf"] = result
            item['CreatedOn'] = "20250910"
            item['ChangedOn'] = "20250918"
            item['CreatedBy'] = "DEVESH"
            item['ChangedBy'] = "DEVESH"
            item['PoNo'] = SAP_JSON['PoLpoIoNoPdf']
            
        SAP_JSON['CreatedOn'] = "20250910"
        SAP_JSON['ChangedOn'] = "20250918"
        SAP_JSON['CreatedBy'] = "DEVESH"
        SAP_JSON['ChangedBy'] = "DEVESH"
        
        return {'status':True}

    except Exception as e:
        LOGS.append(f'106 {str(e)}')
        return {'status':False,'error':str(e)}

def send_pdf_to_sap(pdf_path,inverd_ref_no,status,pdf_name):
    LOGS.append(f'17')
    try:
        # Read PDF and convert to Base64
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        session = requests.Session()

        # --- Step 1: Fetch CSRF Token ---
        token_response = session.get(
            TOKEN_URL,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            headers={"x-csrf-token": "Fetch"},
            verify=False
        )

        if token_response.status_code != 200:
            LOGS.append("112")
            LOGS.append(f"113 {token_response.status_code}")
            LOGS.append(f"114 {token_response.text}")
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "112"
            SAP_JSON['ErrorMsg'] = f"SAP PDF POST API CSRF Token Not Found!"
            return {'status':False ,'error': 'SAP PDF POST API CSRF Token Not Found!'}


        csrf_token = token_response.headers.get("x-csrf-token")
        cookies = token_response.cookies
        LOGS.append(f"14")


        # --- Step 2: Send POST request with CSRF token ---
        headers = {
            "Content-Type": "application/pdf",
            "x-csrf-token": csrf_token,
            "Slug": f'{inverd_ref_no}_{status}_{pdf_name}'
        }

        response = session.post(
            ATTACHMENT_URL,
            data=pdf_base64,
            headers=headers,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            cookies=cookies,
            verify=False
        )

        # --- Step 3: Handle Response ---
        if response.status_code in [200, 201]:
            LOGS.append(f'15')
            res = extract_file_name(response.text)
            
            if (res is not None) or (res != ""):
                LOGS.append(f'20')
                SAP_JSON['ErrorType'] = 'S'
                SAP_JSON['InwardRefNo'] = f'{inverd_ref_no}'
                return {'status':True,'no':res.split('_')[0]}
                
            else:
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "401"
                SAP_JSON['ErrorMsg'] = f"PDF File Name Not Recived From SAP PDF POST API!"
                return {'status':False,'error':'PDF File Name Not Recived From SAP PDF POST API!','no':inverd_ref_no}
        else:
            LOGS.append(f"119")
            LOGS.append(f"117 {response.status_code}")
            LOGS.append(f"118 {response.text}")
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "119"
            SAP_JSON['ErrorMsg'] = f"Recived Bad Response From SAP PDF POST API"
            return {'status':False,'error':'Recived Bad Response From SAP PDF POST API','no':inverd_ref_no}
        

    except Exception as e:
        LOGS.append(f'{str(e)}')
        SAP_JSON['ErrorType'] = 'E'
        SAP_JSON['ErrorNo'] = "801"
        SAP_JSON['ErrorMsg'] = f'{str(e)}'
        return {'status':False,'error':f'{str(e)}','no':inverd_ref_no}


def send_data_to_sap(payload):

    try:
        session = requests.Session()

        # --- Step 1: Fetch CSRF Token ---
        token_response = session.get(
            TOKEN_URL,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            headers={"x-csrf-token": "Fetch"},
            verify=False
        )

        if token_response.status_code != 200:
            LOGS.append("112")
            LOGS.append(f"113 {token_response.status_code}")
            LOGS.append(f"114 {token_response.text}")
            return {'status':False ,'error': 'In SAP API CSRF Token Not Found!'}

        csrf_token = token_response.headers.get("x-csrf-token")
        cookies = token_response.cookies

        LOGS.append(f"14")

        # --- Step 2: Send POST request with CSRF token ---
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-csrf-token": csrf_token
        }

        response = session.post(
            POST_URL,
            json=payload,
            headers=headers,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            cookies=cookies,
            verify=False
        )

        inward_ref_no = response.json().get('d', {}).get('InwardRefNo', "")
        # --- Step 3: Handle Response ---
        if response.status_code in [200, 201]:
            LOGS.append(f'15')

            if inward_ref_no:
                LOGS.append(f"16 {inward_ref_no}")
                return {'status':True ,'no': inward_ref_no}

            else:
                LOGS.append("115")
                return {'status':False ,'error': 'Inward Refrence Number Not Recived!'}

        else:
            
            LOGS.append(f'116')
            LOGS.append(f"117 {response.status_code}")
            LOGS.append(f"118 {response.text}")
            response.raise_for_status()
            return {'status':True ,'no': inward_ref_no if inward_ref_no else ""}
    
    except Exception as e:
        LOGS.append(f"111 {str(e)}")
        return {'status':False ,'error': str(e)}


def api_call(payload):
    try:
        url = os.getenv('API_URL')
        headers = {
            "Authorization": "Bearer YOUR_API_KEY",  # Replace with your actual key or make it configurable
            "Content-Type": "application/json"
        }

        # Send the dict directly to `json=`
        response = requests.post(url, json=payload, headers=headers)

        if response.ok:
            LOGS.append(f'Sucessfully API Called:{response}')
            return response
        else:
            response.raise_for_status()
    
    except Exception as e:
        LOGS.append(f'Error In API Calling Function:{str(e)}')
        return {
            'success': False,
            'error': str(e),
            'stage': 'Error in API calling function!'
        }

# === Step 3: Full pipeline per PDF ===
def process_pdf(pdf_file):
    LOGS.append('2')
    try:
        SAP_JSON['FileName'] = os.path.basename(pdf_file)
        LOGS.append(f'3 {os.path.basename(pdf_file)}')

        result_azure = azure_extract_text(pdf_file)

        if result_azure['status']:
            
            LOGS.append(f'8')
            result_llm = format_with_llm(result_azure['text'])

            if result_llm['status']:
                
                LOGS.append(f'11')
                
                result_final_json = final_json({'data':result_llm['json'],'text':result_azure['text'],'cordinates':result_azure['cordinates']})
                
                LOGS.append(f'12 {result_final_json}')

                if result_final_json['status']:
                    SAP_JSON['ErrorType'] = 'S'
                    LOGS.append(f'13') 

                else:
                    SAP_JSON['ErrorType'] = 'E'
                    SAP_JSON['ErrorNo'] = "801"
                    SAP_JSON['ErrorMsg'] = f"{result_final_json['error']}" 

            else:
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "801"
                SAP_JSON['ErrorMsg'] = f"{result_llm['error']}"
            
        else:
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "801"
            SAP_JSON['ErrorMsg'] = f"{result_azure['error']}"

    except Exception as e:
        LOGS.append(f"102 {os.path.basename(pdf_file)}: {str(e)}")
        SAP_JSON['ErrorType'] = 'E'
        SAP_JSON['ErrorNo'] = "801"
        SAP_JSON['ErrorMsg'] = f"{str(e)}"
       
    finally:

        result = send_data_to_sap(SAP_JSON)    
        
        if result['status']:
            
            if (result['no'] is not None) or (result['no'] != ""): 
                response = send_pdf_to_sap(pdf_file,result['no'],'S',os.path.basename(pdf_file))
                
                result = response

        LOGS.append(f'21')

        with open('log_messages.json', 'r') as file:
            logs = json.load(file)  # correctly loads JSON into a Python dictionary
            logs_steps = []

            for index,value in enumerate(LOGS):
                logs_steps.append(f"Step {index}: {value.replace(value.split()[0],logs[value.split()[0]])}")

            with open('latest/latest_pdf_logs.txt', 'w',encoding='utf-8') as file:
                file.write(str(logs_steps))
        
        with open('latest/latest_pdf_output.txt', 'w',encoding='utf-8') as file:
            file.write(str(SAP_JSON))
        
        result['json'] = SAP_JSON

        return result



# === Step 4: Rolling execution with limited concurrency ===
def process_pdfs(folder_path, max_workers=3):
    
    try:
        pdf_files = sorted(
            [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        )

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pdf = {executor.submit(process_pdf, pdf):pdf for pdf in pdf_files}

            for future in concurrent.futures.as_completed(future_to_pdf):
                pdf_name = future_to_pdf[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    LOGS.append(f"101 {pdf_name}: {e}")

        return results

    except Exception as e:
        LOGS.append('404')

# # === Example Usage ===
# if __name__ == "__main__":

#     folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\test"
#     final_results = process_pdfs(folder_path, max_workers=3)
#     print("\n=== Final Collected Results ===")
#     for r in final_results:
#         print(r)
