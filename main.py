import os
import time
import random
import concurrent.futures
import requests  # for Azure/LLM API calls (placeholder)
import PyPDF2
from dotenv import load_dotenv
import json
load_dotenv()

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


# # === Step 1: Extract text from Azure ===
# @retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
# def azure_extract_text(pdf_file):
#     print(f"🔹 Sending {pdf_file} to Azure Document Intelligence...")
#     # TODO: Replace this with actual Azure SDK or REST API call
#     # Simulate API behavior
#     if random.random() < 0.2:  # 20% chance to fail
#         raise requests.RequestException("Simulated Azure timeout/429")
#     time.sleep(random.randint(2, 4))  # simulate network delay
#     return f"Extracted text from {pdf_file}"


# # === Step 2: Send to LLM ===
# @retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
# def format_with_llm(extracted_text):
#     print("🤖 Sending text to LLM for formatting...")
#     # TODO: Replace with real LLM call
#     if random.random() < 0.1:  # 10% chance to fail
#         raise requests.RequestException("Simulated LLM overload")
#     time.sleep(1)
#     return f"Formatted data: {extracted_text[:40]}..."



# # === Step Custome: Extract text from azure ===
# @retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
# def azure_extract_text(pdf_file):
#     print(f"🔹 Sending {pdf_file} to Azure Document Intelligence...")
#     # TODO: Replace this with actual Azure SDK or REST API call
#     # Simulate API behavior
#     if random.random() < 0.2:  # 20% chance to fail
#         raise requests.RequestException("Simulated Azure timeout/429")
#     time.sleep(random.randint(2, 4))  # simulate network delay
#     return f"Extracted text from {pdf_file}"


# === Step Custome: Extract text from PyMuPdf ===
# @retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(requests.RequestException,))
# def extract_text(pdf_file):
    
#     print(f"🔹 Processing {pdf_file} ...")
    
#     main_text = ""
#     # Open the PDF
#     with open(pdf_file, "rb") as f:
#         reader = PyPDF2.PdfReader(f)
#         # Loop through pages
#         for page_num, page in enumerate(reader.pages, start=1):
#             text = page.extract_text()
#             main_text += f"--- Page {page_num} ---\n"
#             main_text += text if text else "[No extractable text]"
    
#     return main_text

import fitz  # PyMuPDF

def extract_text(pdf_file):
    print(f"🔹 Processing {pdf_file} ...")
    
    main_text = ""
    # Open the PDF with fitz
    with fitz.open(pdf_file) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")  # extract text in reading order
            main_text += f"--- Page {page_num} ---\n"
            main_text += text if text else "[No extractable text]"
    
    return main_text


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
    print('Process PDF Function Called.')
    
    try:
    
        # extracted_text = azure_extract_text(pdf_file)
        # formatted_result = format_with_llm(extracted_text)

        extracted_text = extract_text(pdf_file)
        payload = {'pdf_name': f"{str(pdf_file.split('\\')[-1])}", 'text': f"{str(extracted_text)}"}
        api_response = api_call(payload)

        return api_response

    except Exception as e:

        print(f"❌ Giving up on {pdf_file}: {e}")
        return {'success':False , 'error':str(e)}
    


# === Step 4: Rolling execution with limited concurrency ===
def process_pdfs(folder_path, max_workers=3):
    
    print('Process PDFs Function Called.')
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
                print(f"⚠️ Unhandled exception for {pdf_name}: {e}")

    return results


# === Example Usage ===
if __name__ == "__main__":
    folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\test"
    final_results = process_pdfs(folder_path, max_workers=3)

    print("\n=== Final Collected Results ===")
    for r in final_results:
        print(r)
