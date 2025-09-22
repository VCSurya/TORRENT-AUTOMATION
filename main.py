import os
import time
import random
import concurrent.futures
import requests  # for Azure/LLM API calls (placeholder)
from dotenv import load_dotenv
import json
from openai import AzureOpenAI
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import fitz  # PyMuPDF
from itertools import combinations
from difflib import SequenceMatcher
import json
import re
load_dotenv()

LOGS = []

SAP_JSON = {
        "InwardRefNo" : "",
        "SourceOfDoc" : "",
        "DocMailPerson" : "",
        "InwardDate" : "",
        "PoLpo" : "",
        "GaName" : "",
        "CompanyGstinPdf" : "", 
        "CCompanyGstinPdf" : "",
        "CompanyGstinSap" : "",
        "VendorName" : "",
        "VendorGstin" : "",
        "CVendorGstin" : "",
        "InvoiceNo" : "",
        "CInvoiceNo" : "",
        "InvoiceDate" : "",
        "CInvoiceDate" : "",
        "InvoiceAmount" : "",
        "CInvoiceAmount" : "",
        "PoLpoIoNoPdf" : "",
        "CPoLpoIoNo" : "",
        "IrnNo" : "",
        "CIrnNo" : "",
        "MsmeNo" : "",
        "Status" : "Draft",
        "ModeOfEntry" : "Manual",
        "CreatedOn" : "",
        "CreatedBy" : "",
        "ChangedOn" : "",
        "ChangedBy" : "",
        "FileName" : "",
        "ErrorNo" : "",
        "ErrorMsg" : "",
        "ErrorType" : "",
        "Flag" : "A",
        "DCCHEADERTODCCSES" : []
    }


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
                        print(f"❌ Failed after {max_retries} retries: {e}")
                        raise
                    sleep_time = delay + random.uniform(0, 0.5)  # jitter
                    print(f"⚠️ Error: {e} → retrying in {sleep_time:.1f}s (attempt {attempt+1})")
                    time.sleep(sleep_time)
                    delay *= backoff_factor
        return wrapper
    return decorator

# === Step 1: Extract text from Azure ===
@retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
def azure_extract_text(pdf_file):
    
        try:
            LOGS.append(f"🔹 Sending {pdf_file} to Azure Document Intelligence...")

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

            TEXT = "\n".join(text)

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


            # # Write to output text file
            # with open(output_txt_path, "w", encoding="utf-8") as out_file:
            # Page,X,Y,Height,Width
            # word_dimentions = {}
            
            # for word_info in extracted_words:
            #     word_dimentions[word_info['text']] = [
            #         word_info['page_number'],
            #         round(word_info['x'], 2),
            #         round(word_info['y'], 2),
            #         round(word_info['height'], 2),
            #         round(word_info['width'] + 0.4, 2)
            #     ]

                # f"Page {word_info['page_number']} | "
                # f"Text: {word_info['text']} | "
                # f"x: {word_info['x']:.2f}, y: {word_info['y']:.2f}, "
                # f"width: {word_info['width']+0.4:.2f}, height: {word_info['height']:.2f}\n"
                

            LOGS.append(f"✅ Extraction Complete!")

            return {'status':True,'text':TEXT,'cordinates':extracted_words}

        except Exception as e:
            LOGS.append(f"❌ Error processing {pdf_file}: {str(e)}")
            return {'status':False,'error':str(e)}

# === Step 2: Send to LLM ===
@retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
def format_with_llm(text):

    try:
        LOGS.append("🤖 Sending text to LLM for formatting...")
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

        prompt = f"""
        You are an information extraction system. I will provide you with raw text extracted from an invoice or bill PDF.

        Your task:
        - Extract only the requested fields according to the given JSON schema.
        - Always return strictly valid JSON output, with no explanations, errors, or extra text.

        JSON Schema (follow exactly):
        {{
            "Gst" : [],             // List of GST numbers. If no GST found, return an empty list [].
            "InvoiceNo" : "",       // Invoice or bill number. Return as a string.
            "InvoiceDate" : "",     // Invoice date in YYYY-MM-DD format. If invalid, return "".
            "InvoiceAmount" : "",   // Total invoice amount (numerical value only, no currency symbols).
            "IrnNo" : "",           // 64-character IRN number in hexadecimal format.
            "PoNo" : "",            // Purchase Order number (written as PO, Purchase Order, PO No.)
            "PAN Numbers" : [],     // List of PAN numbers. If none, return an empty list [].
            "Email Id" : "",        // Email ID (if present).
            "SesGrn" : []           // List of SES / GRN / SCROLL numbers (if present).
        }}

        STRICT RULES:
        1. **Do not hallucinate**: If a field is not found, return an empty value as per the schema ("" for strings and [] for lists).
        2. **InvoiceDate**: Normalize to the YYYY-MM-DD format. If the date is not parsable, return "".
        3. **InvoiceAmount**: Must be a numerical value, with no currency symbols. Allow commas, but remove them in the output.
        4. If there are **multiple GST, PAN, or SES/GRN/SCROLL numbers**, include all of them in their respective lists.
        5. **IrnNo**: Must be exactly 64 characters in hexadecimal (0-9, a-f). If the IRN is split across multiple lines, combine them. Return "" if not exactly 64 characters.
        6. **PoNo**: Specifically means **Purchase Order Number**. Extract the complete PO number in all possible variations, including "PO", "PO No.", and "Purchase Order No.". PO number could contain prefixes, sequential numbers, division codes, or other identifiers and may have slashes, dashes, or spaces. Return only the full PO number.
        7. Do not **add, remove, or modify** any fields in the JSON output.
        8. The final output **must** be valid JSON with no extra text.

        Here is the extracted invoice text:
        {text}
        """

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
                    "content": prompt
                }
            ],
            max_tokens=1500,
            temperature=0
        )

        LOGS.append(response)
        content = response.choices[0].message.content
        parsed_data = json.loads(content)  # convert JSON string to dict
        LOGS.append(f">>> JSON \n\n{parsed_data}")
        return {'status':True,'json':parsed_data}

    except Exception as e:
        LOGS.append(f'Error During LLM Calling...:{str(e)}')
        return {'status':False,'error':str(e)}

def final_json(JSON):
    
    try:
        
        gst_no = {
            "24AAGCT7889P1Z9",
            "24AAGCT7889P2Z8",
            "27AAGCT7889P1Z3",
            "27AAGCT7889P1Z3",
            "03AAGCT7889P1ZD",
            "34AAGCT7889P1Z8",
            "08AAGCT7889P1Z3",
            "08AAGCT7889P1Z3",
            "33AAGCT7889P1ZA",
            "36AAGCT7889P1Z4",
            "09AAGCT7889P1Z1",
            "24AAHCT5406D1ZO",
            "33AAHCT5406D1ZP",
            "24AAHCD1012H1ZA",
            "08AAHCD1012H1Z4",
            "24AAICT6216A1ZR",
            "08AAICT6216A1ZL"
        }

        def gst_validations(list_of_gst):
            try:
                list_of_gst = list(set(list_of_gst))
                company_gst = list_of_gst[0]
                vendor_gst = list_of_gst[1]

                for i in list_of_gst:
                    if len(i) == 15:
                        if i in gst_no:
                            company_gst = i
                        else:
                            vendor_gst = i

                return {'status':True , "CompanyGstinPdf":company_gst,"VendorGstin":vendor_gst}
            except Exception as e:
                return {'status':False , "error":str(e)}

        def get_irn_number(lst):
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

        def get_closest_10_digit_string(text, input_string):
            # Extract all 10-digit substrings using regular expressions
            potential_matches = re.findall(r'\d{10}', text)

            if not potential_matches:
                return None, 0  # If no 10-digit numbers are found
            
            # Initialize variables to store the best match and its similarity
            best_match = None
            highest_similarity = 0

            # Function to calculate similarity using SequenceMatcher
            def calculate_similarity(str1, str2):
                return SequenceMatcher(None, str1, str2).ratio()

            # Compare each 10-digit substring with the input string
            for match in potential_matches:
                similarity = calculate_similarity(input_string, match)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = match

            return best_match, highest_similarity

        gst_result = gst_validations(JSON['data']['Gst'])

        if gst_result['status']:
            SAP_JSON['CompanyGstinPdf'] = gst_result['CompanyGstinPdf']
            SAP_JSON['VendorGstin'] = gst_result['VendorGstin']

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
                closest_string, similarity = get_closest_10_digit_string(JSON['text'], data)
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
        SAP_JSON['InvoiceDate'] = JSON['data']['InvoiceDate']
        SAP_JSON['InvoiceAmount'] = JSON['data']['InvoiceAmount']
        SAP_JSON['PoLpoIoNoPdf'] = JSON['data']['PoNo']
        
        # SAP_JSON['CPoLpoIoNo'] = JSON['data']['Email Id']
        return True

    except Exception as e:
        return False

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
            return response
        else:
            response.raise_for_status()
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stage': 'Error in API calling function!'
        }

# === Step 3: Full pipeline per PDF ===
def process_pdf(pdf_file):
    LOGS.append('Process PDF Function Called.')
    
    try:
        SAP_JSON['FileName'] = str(pdf_file)
        result_azure = azure_extract_text(pdf_file)

        if result_azure['status']:
            result_llm = format_with_llm(result_azure['text'])
            if result_llm['status']:
                result_final_json = final_json({'data':result_llm['json'],'text':result_azure['text'],'cordinates':result_azure['cordinates']})
                if result_final_json:
                    SAP_JSON['ErrorType'] = 'S'
                    print('>>'*5,'\n') 
                    print(SAP_JSON) 
                    print({'data':result_llm['json'],'text':result_azure['text'],'cordinates':result_azure['cordinates']})
                    # LOGS.append(result_final_json)
        
        # payload = {'pdf_name': f"{str(pdf_file.split('\\')[-1])}", 'text': f"{str(extracted_text)}"}
        # api_response = api_call(payload)

        # return api_response
        

    except Exception as e:

        LOGS.append(f"❌ Giving up on {pdf_file}: {e}")
        return {'success':False , 'error':str(e)}
    


# === Step 4: Rolling execution with limited concurrency ===
def process_pdfs(folder_path, max_workers=3):
    
    LOGS.append('Process PDFs Function Called.')
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
                LOGS.append(f"⚠️ Unhandled exception for {pdf_name}: {e}")

    return results


# === Example Usage ===
if __name__ == "__main__":
    folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\test"
    final_results = process_pdfs(folder_path, max_workers=3)
    # print(LOGS)
    print("\n=== Final Collected Results ===")
    for r in final_results:
        print(r)
