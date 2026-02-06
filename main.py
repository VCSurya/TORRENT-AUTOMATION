import os
import re
import cv2 
import copy
import fitz
import json
import httpx
import shutil
import base64
import tempfile
import requests
import traceback
import concurrent.futures
from qreader import QReader
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI
from itertools import combinations
from pdf2image import convert_from_path
from difflib import SequenceMatcher,get_close_matches
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

load_dotenv()
PROMPT_NO = 0
LOGS = []
# Get the directory where the current script is located
SCRTPT_DIR = os.path.dirname(os.path.abspath(__file__))
POPLOR_PATH = r"poppler-24.08.0\Library\bin"

# --- SAP URLs ---
BASE_URL = os.getenv('SAP_BASE_URL')
POST_URL = f"{BASE_URL}/{os.getenv('Z_TABLE_DATA_STORE_ENTETY_SET_NAME')}"
ATTACHMENT_URL = f"{BASE_URL}/{os.getenv('DMS_DOCUMENT_SAVE_ENTETY_SET_NAME')}"
# For CSRF token fetch, root or entityset is enough (no $expand needed)
TOKEN_URL = f"{BASE_URL}/"

# --- SAP Credentials ---
SAP_USERNAME = os.getenv('SAP_USERNAME')   
SAP_PASSWORD = os.getenv('SAP_PASSWORD')

### >>> Load the PAN Numbers From TXT File
PAN_NO_URL = f"{BASE_URL}/{os.getenv('GET_PAN_NUMBERS_ENTETY_SET_NAME')}"

prompt_path  = os.path.join(SCRTPT_DIR, 'pan.txt')

with open(prompt_path, 'r') as file:
    PAN_NO = set(file.read().splitlines())

# MAKE CONNECTION FOR TLS handshake
timeout = httpx.Timeout(connect=45.0, read=30.0,write=30.0, pool=30.0)


http_client = httpx.Client(
    timeout=timeout,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=True,   # safe even if you think no proxy
)

aoai_client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key = os.getenv("AZURE_OPENAI_KEY") ,
    api_version="2024-02-01",
    http_client=http_client,
    timeout=30.0,
    max_retries=1
)


def call_model(prompt):
    try:
        return aoai_client.chat.completions.create(
            model= os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                response_format={"type": "json_object"},  # 👈 Force valid JSON
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. Always respond strictly in JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1200,
                temperature=0.2,
                top_p = 1,
                frequency_penalty = 0,
                presence_penalty = 0,
        )
    except:
        LOGS.append(f"132 {traceback.print_exc()}")
        return {}

def pan_numbers():
    
    pan_numbers = []

    try:

        # Session and headers
        session = requests.Session()
        headers = {
            "x-csrf-token": "Fetch",
            "Accept": "application/json",
            "sap-client": os.getenv("SAP_CLIENT")
        }


        token_response = session.get(
            PAN_NO_URL,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            headers=headers,
            verify=False  # remove or set to True in production with proper certs
        )

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"126 {str(e)}")
    else:
        status = token_response.status_code
        if status != 200:
            LOGS.append(f"112 Durring GET PAN Numbers")
            LOGS.append(f"113 {token_response.status_code}")
            LOGS.append(f"114 {token_response.text}")
        else:
            try:
                data = token_response.json()
                pan_numbers = [entry['PanNo'] for entry in data['d']['results']]
                LOGS.append(f"24") if len(pan_numbers) > 0 else LOGS.append(f"129") 
            except:
                LOGS.append(f"127")
    
    return pan_numbers

def decode_qr_data(qr_string):
    try:
        # Remove whitespace/newlines
        qr_string = ''.join(qr_string.split())
        
        # Split by dots
        segments = qr_string.split('.')
        
        if len(segments) == 3:
            # Proper signed JWT (header.payload.signature)
            header_b64, payload_b64, signature_b64 = segments
        elif len(segments) == 2:
            # Unsigned JWT / 2-segment token
            header_b64, payload_b64 = segments
        else:
            LOGS.append(f"124 {len(segments)}")
        # Helper function for base64url decoding
        def b64url_decode(b64_string):
            b64_string += '=' * (-len(b64_string) % 4)  # add padding
            return base64.urlsafe_b64decode(b64_string)
        
        # Decode JSON
        header = json.loads(b64url_decode(header_b64))
        payload = json.loads(b64url_decode(payload_b64))
        
        return header, payload

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"121 {str(e)}")
        return None

def detect_qrs_from_image(qr_image_path):

    try:
        qr_img = cv2.imread(qr_image_path)

        detector = QReader()
        # Detect and decode the QRs within the image
        decodedQR, QRlocation = detector.detect_and_decode(image=qr_img, return_detections=True)
        if len(decodedQR) != 0:
            if decodedQR[0] != None:
                header, payload = decode_qr_data(decodedQR[0])
                if payload.get("data"):
                    return payload.get("data")
                else:
                    return None
            else:
                return None    
        else:
            return None
    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"122 {str(e)}")
        return None

def pdf_to_images_pymupdf(pdf_file_path, dpi=300):
    images = []
    zoom = dpi / 72.0  # 72 DPI base
    mat = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_file_path) as doc:
        for page_index in range(len(doc)):
            pix = doc[page_index].get_pixmap(matrix=mat, alpha=False)
            images.append(pix)  # you can save via pix.save("out.png")
    return images

def pdf_to_image(pdf_file_path):
    
    try:
    
        list_images_paths = []            
        images = convert_from_path(pdf_file_path,poppler_path=POPLOR_PATH,dpi=300)
        data = None
        with tempfile.TemporaryDirectory(dir=os.path.join(os.getcwd(), 'temp')) as temp_dir:

            for i,image in enumerate(images):
                save_image_dir = os.path.join(temp_dir,f"{i}.png")
                image.save(save_image_dir,"PNG") 
                list_images_paths.append(save_image_dir)

            for qr_image in os.listdir(temp_dir):
                result = detect_qrs_from_image(os.path.abspath(os.path.join(temp_dir,qr_image)))
                if result != None:
                    if "Irn" in result:
                        LOGS.append(f"23")
                        data = json.loads(result)
                        break
 
        return {"status":False if data is None else True,"data":data}
    
    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"123 {str(e)}")
        return {"status":False,"error":str(e), "error_code":"123"}


# === Step 1: Extract text from Azure ===
def azure_extract_text(pdf_file,manual = 0):
    
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
                    body=f,
                    pages=os.getenv('AT_EMAIL_PAGES') if manual == 0 else os.getenv('AT_MANUAL_PAGES')
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
                return {'status':False,'error':"Text Not Extracted From AZURE", "error_code":"104"}

        except Exception:
            e = traceback.format_exc()
            LOGS.append(f"103 {str(e)}")
            return {'status':False,'error':str(e), "error_code":"103"}

# === Step 2: Send to LLM ===
def format_with_llm(text):

    try:
        
        # print("Load Prompt:",PROMPT_NO)
        ### >>> Load the Prompt Tamplate From TXT File acording to need
        propmt = ""
        prompt_path  = os.path.join(SCRTPT_DIR, 'prompt_1.txt' if PROMPT_NO == 1 else 'prompt_0.txt')
        with open(prompt_path, 'r') as file:
            propmt = file.read()

        propmt = propmt + '\n' + text

        # Call GPT-4.1-mini with forced JSON output
        response = call_model(propmt)

        with open('latest/latest_pdf_open_ai_respons.txt', 'w',encoding='utf-8') as file:
            file.write(str(response))

        LOGS.append(f"9")
        content = response.choices[0].message.content
        parsed_data = json.loads(content)  # convert JSON string to dict
        LOGS.append(f"10")
        return {'status':True,'json':parsed_data}

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f'105 {str(e)}')
        return {'status':False,'error':str(e), "error_code":"105"}

def final_json(JSON,SAP_JSON,Mode_Of_Entry,Created_On,Created_By):
    
    try:

        def gst_validations(gst_list):
            
            def similarity(a, b):
                return SequenceMatcher(None, a, b).ratio()
            
            try:    
                best_gst = None
                best_score = -1
                
                for gst in gst_list:
                    gst_pan_part = gst[2:12]  # GST PAN is at position 3-12
                    list_of_pan_numbers = pan_numbers()
                    for pan in list_of_pan_numbers if len(list_of_pan_numbers) > 0 else PAN_NO:
                        score = similarity(gst_pan_part, pan)
                        if score > best_score:
                            best_score = score
                            best_gst = gst
                
                gst_list.remove(best_gst)
                vendor_gst = gst_list[0] if len(gst_list) > 0 else "" 
                
                return {'status':True , "CompanyGstinPdf":best_gst,"VendorGstin":vendor_gst}
            
            except Exception:
                e = traceback.format_exc()
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

            except Exception:
                e = traceback.format_exc()
                LOGS.append(f'108 {str(e)}')

        def get_closest_10_digit_string(text, input_string):

            if '-' in input_string:
                input_string = input_string.replace("/","1").replace("\\","1")
                part_1 =  input_string.split("-")[0]
                part_2 =  input_string.split("-")[1]
                total_len = len(part_2) + len (part_1)
                if total_len < 10:
                    return input_string.replace("-","0"*(10-total_len))
            
            best_match = None
            # Initialize variables to store the best match and its similarity
            highest_similarity = 0
            
            try:
                # Extract all 10-digit substrings using regular expressions
                potential_matches = re.findall(r'\d{10}', text)

                if not potential_matches:
                    return None  # If no 10-digit numbers are found
                
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
            
            except Exception:
                e = traceback.format_exc()
                LOGS.append(f'109 {str(e)}')
                return best_match
                
        def convert_normalized_to_absolute(cordinates): # [ page_number -0 , x-1, y-2, width-3, height-4, page_width-5, page_height-6 ]
            try:
                x0 = cordinates[1] * 72
                y0 = cordinates[2] * 72
                x1 = cordinates[3] * 72
                y1 = cordinates[4] * 72
                return f"{cordinates[0]},{x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}"
            except:
                e = traceback.format_exc()
                LOGS.append(f'110 {str(e)}')
                return f"{cordinates[0]},{cordinates[1]},{cordinates[2]},{cordinates[3]},{cordinates[4]}"

        def find_closest(data: dict, target: str) -> str:
            """
            Find the key in `data` that best matches `target`.
            Priority:
            1. Exact key match (case-sensitive)
            2. Substring match
            3. Closest fuzzy match
            Returns the matched key.
            """

            if not data:
                return None

            keys = list(data.keys())
            target_str = str(target)
            # 1️⃣ Exact key match
            if target_str in keys:
                matched_key = target_str

            else:
                # 2️⃣ Substring match
                substring_matches = [k for k in keys if target_str in k]
                if substring_matches:
                    matched_key = substring_matches[0]

                else:
                    # 3️⃣ Closest fuzzy match
                    matches = get_close_matches(target_str, keys, n=1, cutoff=0.7)
                    if matches:
                        matched_key = matches[0]
                    else:
                        # Fallback: absolute best similarity ratio
                        matched_key = max(keys, key=lambda k: SequenceMatcher(None, target_str, k).ratio())

            # 🧩 Prepare structured coordinates
            coords_list = []
            for coord in data[matched_key]:
                if len(coord) == 7:
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
                    coords_list.append({'raw': coord})

            return matched_key

        def valid_po(po_no):
            
            try:
                new = po_no.replace(" ","").split('/')[-1]
                
                if new.isdigit() and len(new) <= 10:
                    return new
                else:
                    numbers = re.findall(r'\d+',po_no)
                    large_number = max(numbers,key=int)
                    
                    if 0 < len(large_number) <= 10: 
                        JSON['data']['PoNo'] = large_number
                        return large_number
                    else:
                        return po_no
            
            except:
                e = traceback.format_exc()
                LOGS.append(f'131 {str(e)}')
                return po_no
        
        def to_yyyymmdd(date_str: str) -> str:
            for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y%m%d")
                except ValueError:
                    return date_str.replace("-","").replace("/","")


        with open('latest/latest_pdf_azure_text_cordinates.json', 'w', encoding='utf-8') as file:
            json.dump(JSON['cordinates'], file, ensure_ascii=False, indent=4)
        
        if PROMPT_NO == 0:

            # GST Validation
            
            gst_result = None
            if JSON['data']['Gst'] != "":
                gst_result = gst_validations(JSON['data']['Gst'])

            if gst_result['status']:
                SAP_JSON['CompanyGstinPdf'] = gst_result['CompanyGstinPdf'].replace(".","").replace(",","")
                SAP_JSON['VendorGstin'] = gst_result['VendorGstin']
            else:
                LOGS.append(f'107 {gst_result}')
            
            # IRN Validation
            SAP_JSON['IrnNo'] = JSON['data']['IrnNo'] 
            if len(JSON['data']['IrnNo']) != 64:
                pattern = r'\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*[0-9])[0-9a-fA-F]{10,64}\b'
                matches = re.findall(pattern, JSON['text']) # Find all matches
                if len(matches) != 0:
                    res = get_irn_number(matches)
                    if res != "":
                        SAP_JSON['IrnNo'] = res

            #  Value SAVE IN MAIN SAP JSON 

            SAP_JSON['InvoiceNo'] = JSON['data']['InvoiceNo']
            SAP_JSON['InvoiceAmount'] = JSON['data']['InvoiceAmount']
            
            if JSON['data']['InvoiceDate'] != "":
                
                SAP_JSON['InvoiceDate'] = JSON['data']['InvoiceDate'].replace("-","") 
            
            else:
                SAP_JSON['InvoiceDate'] = to_yyyymmdd(JSON['data']['InvoiceOriginalDate'])
        
        # SCS/GRN Validation with nested loop

        total_scs_no = []

        for index, data in enumerate(set(JSON['data']['SesGrn'])):
            
            ses_no = data

            # Check if data is not exactly 10-digit numeric
            if not (len(data) == 10 and data.isdigit()):
                LOGS.append(f"22 {data}")
                closest_string = get_closest_10_digit_string(JSON['text'],data)
                if closest_string:
                    ses_no = closest_string
                else:
                    continue
            
            if ses_no not in total_scs_no:
                
                SAP_JSON['DCCHEADERTODCCSES'].append(
                    {
                        "InwardRefNo": "",
                        "PoNo": "",
                        "SesGrnScrollNoPdf": ses_no,
                        "ItemNo": f"{index+1}",
                        "SesGrnScrollNoSap": "",
                        "ParkDocNo": "",
                        "Amount": "",
                        "CreatedOn": "",
                        "Zindicator": "",
                        "CreatedBy": "",
                        "CSesGrnScrollNoPdf": "",
                        "ChangedOn": "",
                        "ChangedBy": "",
                        "CreatedOnTime" : datetime.now().strftime("%H:%M:%S"),
                    }
                )

                total_scs_no.append(ses_no)
        
        #  Value SAVE IN MAIN SAP JSON 

        SAP_JSON['CreatedOn'] = f"{Created_On}"
        SAP_JSON['CreatedBy'] = f"{Created_By}"
        SAP_JSON['ModeOfEntry'] = f"{Mode_Of_Entry}"
        SAP_JSON['PoLpoIoNoPdf'] = valid_po(JSON['data']['PoNo'])
        
        # FIND THE CORDINATES OF FIELDS

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

        if JSON['data']['InvoiceOriginalDate'] != "":
            closest_key = find_closest(JSON['cordinates'], str(JSON['data']['InvoiceOriginalDate']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CInvoiceDate"] = result

        if SAP_JSON['InvoiceAmount'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['InvoiceAmount']))
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CInvoiceAmount"] = result

        if SAP_JSON['PoLpoIoNoPdf'] != "":
            closest_key = find_closest(JSON['cordinates'], str(JSON['data']['PoNo']))
            try:
                keys = list(JSON['cordinates'].keys())
                existing = keys.index(closest_key)

                remaining = 10 - len(SAP_JSON['PoLpoIoNoPdf'])
                if keys[existing+1].isdigit():
                    new_value = keys[existing+1]
                    if len(new_value) <= remaining:

                        SAP_JSON['PoLpoIoNoPdf'] = f"{SAP_JSON['PoLpoIoNoPdf']}{new_value}"
                
                        if JSON['cordinates'][closest_key][0][0] == JSON['cordinates'][keys[existing+1]][0][0] and JSON['cordinates'][closest_key][0][5] == JSON['cordinates'][keys[existing+1]][0][5] and JSON['cordinates'][closest_key][0][6] == JSON['cordinates'][keys[existing+1]][0][6]:

                            if JSON['cordinates'][closest_key][0][3] < JSON['cordinates'][keys[existing+1]][0][3]:
                                JSON['cordinates'][closest_key][0][3] = JSON['cordinates'][keys[existing+1]][0][3] 
                            
                            JSON['cordinates'][closest_key][0][4] = JSON['cordinates'][closest_key][0][4] + JSON['cordinates'][keys[existing+1]][0][4]
            
            except:
                pass
            
            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CPoLpoIoNo"] = result

        if SAP_JSON['IrnNo'] != "":
            closest_key = find_closest(JSON['cordinates'], str(SAP_JSON['IrnNo']))
            
            if len(closest_key) < 64:
                
                irn_no = closest_key
                new_coo = copy.deepcopy(JSON['cordinates'])
                new_coo.pop(closest_key)

                while True:

                    new_closest_key = find_closest(new_coo, str(SAP_JSON['IrnNo']))
                    irn_no = f"{irn_no}{new_closest_key}"

                    if JSON['cordinates'][closest_key][0][0] == JSON['cordinates'][new_closest_key][0][0] and JSON['cordinates'][closest_key][0][5] == JSON['cordinates'][new_closest_key][0][5] and JSON['cordinates'][closest_key][0][6] == JSON['cordinates'][new_closest_key][0][6]:
                    
                        
                        if JSON['cordinates'][new_closest_key][0][3] > JSON['cordinates'][closest_key][0][3]:
                            JSON['cordinates'][closest_key][0][3] = JSON['cordinates'][new_closest_key][0][3] 
                        
                        if JSON['cordinates'][new_closest_key][0][2] < JSON['cordinates'][closest_key][0][2]:
                            JSON['cordinates'][closest_key][0][2] = JSON['cordinates'][new_closest_key][0][2] 
                        

                        JSON['cordinates'][closest_key][0][4] = JSON['cordinates'][closest_key][0][4] + JSON['cordinates'][new_closest_key][0][4] 
                    

                    if len(irn_no) >= 64:
                        break
                    else:
                        new_coo.pop(new_closest_key)
                

            result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])
            SAP_JSON["CIrnNo"] = result

        for item in SAP_JSON['DCCHEADERTODCCSES']:
            ses_grn_scroll_no_pdf = item['SesGrnScrollNoPdf']
            
            if ses_grn_scroll_no_pdf != "":
                closest_key = find_closest(JSON['cordinates'], str(ses_grn_scroll_no_pdf))
                # Assuming `convert_normalized_to_absolute` is a function defined elsewhere
                result = convert_normalized_to_absolute(JSON['cordinates'][closest_key][0])        
                # Here we update the item directly in the list
                item["CSesGrnScrollNoPdf"] = result
            
            item['CreatedOn'] = f"{Created_On}"
            item['CreatedBy'] = f"{Created_By}"
            item['PoNo'] = SAP_JSON['PoLpoIoNoPdf']
        
        return {'status':True}

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f'106 {str(e)}')
        return {'status':False,'error':str(e), "error_code":"106"}

def send_pdf_to_sap(pdf_path,inverd_ref_no,SAP_JSON):
    LOGS.append(f'17')
    try:
        # Read PDF and convert to Base64
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        session = requests.Session()

        # --- Step 1: Fetch CSRF Token ---
        token_response = session.get(
            POST_URL,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            headers={"x-csrf-token": "Fetch","sap-client": os.getenv("SAP_CLIENT")},
            verify=False
        )

        if token_response.status_code != 200:
            LOGS.append("112")
            LOGS.append(f"113 {token_response.status_code}")
            LOGS.append(f"114 {token_response.text}")
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "112"
            SAP_JSON['ErrorMsg'] = f"SAP PDF POST API CSRF Token Not Found!"
            return {'status':False ,'error': 'SAP PDF POST API CSRF Token Not Found!', "error_code":"112"}


        csrf_token = token_response.headers.get("x-csrf-token")
        cookies = token_response.cookies
        LOGS.append(f"14")


        # --- Step 2: Send POST request with CSRF token ---
        headers = {
            "Content-Type": "application/pdf",
            "x-csrf-token": csrf_token,
            "Slug": f'{inverd_ref_no}.pdf',
            "Accept": "application/json"
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
            
            DMS_NO = response.json().get("d",None).get("DocumentNo",None)
            
            if (DMS_NO is not None) or (DMS_NO != ""):
                LOGS.append(f'20')
                SAP_JSON['ErrorType'] = 'S'
                return {'status':True,'no':inverd_ref_no}
                
            else:
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "401"
                SAP_JSON['ErrorMsg'] = f"PDF File Name Not Recived From SAP PDF POST API!"
                return {'status':False,'error':'PDF File Name Not Recived From SAP PDF POST API!','no':inverd_ref_no, "error_code":"401"}
        else:
            LOGS.append(f"119")
            LOGS.append(f"117 {response.status_code}")
            LOGS.append(f"118 {response.text}")
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "119"
            SAP_JSON['ErrorMsg'] = f"Recived Bad Response From SAP PDF POST API"
            return {'status':False,'error':'Recived Bad Response From SAP PDF POST API','no':inverd_ref_no, "error_code":"119"}
        

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f'125 {str(e)}')
        SAP_JSON['ErrorType'] = 'E'
        SAP_JSON['ErrorNo'] = "801"
        SAP_JSON['ErrorMsg'] = f'{str(e)}'
        return {'status':False,'error':f'{str(e)}','no':inverd_ref_no, "error_code":"125"}

def send_data_to_sap(SAP_JSON):

    try:
        session = requests.Session()

        # --- Step 1: Fetch CSRF Token ---
        token_response = session.get(
            TOKEN_URL,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            headers={"x-csrf-token": "Fetch","sap-client": os.getenv("SAP_CLIENT")},
            verify=False
        )

        if token_response.status_code != 200:
            LOGS.append("112")
            LOGS.append(f"113 {token_response.status_code}")
            LOGS.append(f"114 {token_response.text}")
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "112"
            SAP_JSON['ErrorMsg'] = f'In SAP API CSRF Token Not Found!'
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
            json=SAP_JSON,
            headers=headers,
            auth=(SAP_USERNAME, SAP_PASSWORD),
            cookies=cookies,
            verify=False
        )
        inward_ref_no = response.json().get('d', {}).get('InwardRefNo', "")
        from_sap_status = response.json().get('d', {}).get('Status', "")
        DuplicateMsg = response.json().get('d', {}).get('DuplicateMsg', "")
        LOGS.append(f"16 {inward_ref_no} - {from_sap_status}")

        with open('latest/latest_sap_response.json', 'w',encoding='utf-8') as file:
                json.dump(response.json(), file, ensure_ascii=False, indent=4)

        # --- Step 3: Handle Response ---
        if response.status_code in [200, 201]:
            LOGS.append(f'15')

            if inward_ref_no != "":
                LOGS.append(f"16 {inward_ref_no} - {from_sap_status}")
                SAP_JSON['ErrorType'] = 'S'
                SAP_JSON['Status'] = str(from_sap_status)
                SAP_JSON['DuplicateMsg'] = str(DuplicateMsg)
                SAP_JSON['InwardRefNo'] = f'{inward_ref_no}'

                for item in SAP_JSON['DCCHEADERTODCCSES']:
                    item['InwardRefNo'] = f"{inward_ref_no}"
                return {'status':True ,'no': inward_ref_no , 'Status':from_sap_status}

            else:
                LOGS.append("115")
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "115"
                SAP_JSON['ErrorMsg'] = f'Inward Refrence Number Not Recived!'
                return {'status':False ,'error': 'Inward Refrence Number Not Recived!',"error_code":"115"}

        else:
            if inward_ref_no:
                LOGS.append(f'116')
                LOGS.append(f"117 {response.status_code}")
                LOGS.append(f"118 {response.text}")
                SAP_JSON['Status'] = str(from_sap_status)
                SAP_JSON['ErrorType'] = 'S'
                return {'status':True ,'no': inward_ref_no,'Status':from_sap_status}
            else:
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "111"
                SAP_JSON['ErrorMsg'] = f'{response.json().get('error').get('message').get('value')}'
                return {'status':False ,'error': f"{response.json().get('error').get('message').get('value')}","error_code":"111"}
    
    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"130 {str(e)}")
        SAP_JSON['ErrorType'] = 'E'
        SAP_JSON['ErrorNo'] = "130"
        SAP_JSON['ErrorMsg'] = f'{e}'
        return {'status':False ,'error': str(e) , "error_code":"130"}

# === Step 3: Full pipeline per PDF ===
def process_pdf(pdf_file,email_data,Mode_Of_Entry = "BOT",Created_On=f"{datetime.now().strftime('%Y%m%d')}",Created_By="BOT"):
    
    LOGS.clear()
    global PROMPT_NO
    ### >>> Load the SAP JSON Tamplate
    sap_file_path = os.path.join(SCRTPT_DIR, 'sap.json')
    with open(sap_file_path, 'r') as file:
        SAP_JSON = json.load(file)

    LOGS.append('2')
    try:
        SAP_JSON['FileName'] = os.path.basename(pdf_file)
        LOGS.append(f'3 {os.path.basename(pdf_file)}')
        
        # Here we getting the data from qr code which is availabel in pdf
        PROMPT_NO = 0
        result_of_extracted_data_from_qr = pdf_to_image(pdf_file)
    
        if result_of_extracted_data_from_qr['status']:
            PROMPT_NO = 1
            SAP_JSON['CompanyGstinPdf'] = result_of_extracted_data_from_qr['data']['BuyerGstin']
            SAP_JSON['VendorGstin'] = result_of_extracted_data_from_qr['data']['SellerGstin']
            SAP_JSON['InvoiceNo'] = result_of_extracted_data_from_qr['data']['DocNo']
            SAP_JSON['InvoiceDate'] = result_of_extracted_data_from_qr['data']['DocDt'].split('/')[2] + result_of_extracted_data_from_qr['data']['DocDt'].split('/')[1] + result_of_extracted_data_from_qr['data']['DocDt'].split('/')[0]
            SAP_JSON['InvoiceAmount'] = str(result_of_extracted_data_from_qr['data']['TotInvVal'])
            SAP_JSON['IrnNo'] = result_of_extracted_data_from_qr['data']['Irn']
            SAP_JSON['IndCompanygstinpdf'] = "QR" 
            SAP_JSON['IndVendorgstinpdf'] = "QR"
            SAP_JSON['IndInvoiceno'] = "QR"
            SAP_JSON['IndInvoicedate'] = "QR"
            SAP_JSON['IndInvoiceamount'] = "QR"
            SAP_JSON['IndIrnno'] = "QR"
        
        manual = 0 if Mode_Of_Entry == "Bot" else 1
        result_azure = azure_extract_text(pdf_file,manual)

        if result_azure['status']:
            
            LOGS.append(f'8')
            result_llm = format_with_llm(result_azure['text'])

            if result_llm.get('status') and result_llm.get('json').get('Invoice'):
                
                LOGS.append(f'11')
                
                result_final_json = final_json({'data':result_llm['json'],'text':result_azure['text'],'cordinates':result_azure['cordinates']},SAP_JSON,Mode_Of_Entry,Created_On,Created_By)
                
                LOGS.append(f'12 {result_final_json}')

                if result_final_json['status']:
                    SAP_JSON['ErrorType'] = 'S'
                    LOGS.append(f'13') 

                else:
                    SAP_JSON['ErrorType'] = 'E'
                    SAP_JSON['ErrorNo'] = "802"
                    SAP_JSON['ErrorMsg'] = f"{result_final_json['error']}"
            
            elif not result_llm.get('json').get('Invoice'):
                LOGS.append(f'25')
                SAP_JSON['Invoice'] = False
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "25"
                SAP_JSON['ErrorMsg'] = f"Not Invoice Document!"
            
            else:
                SAP_JSON['ErrorType'] = 'E'
                SAP_JSON['ErrorNo'] = "803"
                SAP_JSON['ErrorMsg'] = f"{result_llm['error']}"
            
        else:
            SAP_JSON['ErrorType'] = 'E'
            SAP_JSON['ErrorNo'] = "804"
            SAP_JSON['ErrorMsg'] = f"{result_azure['error']}"

    except Exception:
        e = traceback.format_exc()
        LOGS.append(f"102 {os.path.basename(pdf_file)}: {str(e)}")
        SAP_JSON['ErrorType'] = 'E'
        SAP_JSON['ErrorNo'] = "805"
        SAP_JSON['ErrorMsg'] = f"{str(e)}"
       
    finally:

        try:
            SAP_JSON["VendorEmailP"] = email_data.get("vandor_email","")
            SAP_JSON["DocMailPerson"] = email_data.get("vandor_email","")
            SAP_JSON["EmailDateTimeP"] = email_data.get("email_date_time","")
            SAP_JSON["EmailSubjectP"] = email_data.get("email_subject","")
            SAP_JSON["SourceOfDoc"] = email_data.get("SourceOfDoc","")
            SAP_JSON["CreatedOnTime"] = datetime.now().strftime("%H:%M:%S")

            result = {'status':False}
            result['PDF_FileName'] = str(os.path.basename(pdf_file))
            
            if SAP_JSON['Invoice']:
                SAP_JSON.pop('Invoice')
                result = send_data_to_sap(SAP_JSON) 
   
            if result['status']:
                
                if result['no'] != "": 
                    response = send_pdf_to_sap(pdf_file,result['no'],SAP_JSON)
                    result = response
                else:
                    LOGS.append(f'120')

            LOGS.append(f'21 >>>>')

            with open('log_messages.json', 'r') as file:
                logs = json.load(file)  # correctly loads JSON into a Python dictionary
                logs_steps = []
                for index,value in enumerate(LOGS):
                    logs_steps.append(f"Step {index} ({value.split()[0]}): {value.replace(value.split()[0],logs[value.split()[0]])}")

                with open('latest/latest_pdf_logs.txt', 'w',encoding='utf-8') as file:
                    file.write(str(logs_steps))

                if not result['status']:
                    result['logs'] = logs_steps
            
            with open('latest/latest_pdf_output.json', 'w',encoding='utf-8') as file:
                json.dump(SAP_JSON, file, ensure_ascii=False, indent=4)
            
            destination_path = os.path.join('latest/', "latest.pdf")
            shutil.copy(pdf_file,destination_path)

            result['json'] = SAP_JSON
            result['PDF_FileName'] = str(os.path.basename(pdf_file))

            return result

        except:
            import traceback
            print(f"(+) Failed into finally block main.py, ",traceback.print_exc())     
            return {}

# === Step 4: Rolling execution with limited concurrency ===
def process_pdfs(folder_path, email_data,max_workers=3):
    
    try:
        pdf_files = sorted(
            [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        )

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pdf = {executor.submit(process_pdf, pdf,email_data):pdf for pdf in pdf_files}

            for future in concurrent.futures.as_completed(future_to_pdf):
                pdf_name = future_to_pdf[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    e = traceback.format_exc()
                    LOGS.append(f"101 {pdf_name}: {e}")

        return {'status':True,"result":results}

    except Exception:
        e = traceback.format_exc()
        return {'status':False,"error":str(e)}

# # === Example Usage ===
# if __name__ == "__main__":

#     email_data = {
#                         "vandor_email":"",
#                         "email_date_time":"",
#                         "email_subject":"",
#                         "SourceOfDoc":""
#         }
    
#     folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\test.pdf"
#     final_results = process_pdf(folder_path,email_data)
#     print("\n=== Final Collected Results ===")
#     # for r in final_results:
#     #     print(r)

#     print(final_results)
