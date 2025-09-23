import os
import time
import random
import concurrent.futures
import requests
import json
import re
import logging
from itertools import combinations
from difflib import SequenceMatcher
from dotenv import load_dotenv

import fitz  # PyMuPDF
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

# === ENVIRONMENT ===
load_dotenv()

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === GLOBAL JSON TEMPLATE ===
SAP_JSON_TEMPLATE = {
    "InwardRefNo": "",
    "SourceOfDoc": "",
    "DocMailPerson": "",
    "InwardDate": "",
    "PoLpo": "",
    "GaName": "",
    "CompanyGstinPdf": "",
    "CCompanyGstinPdf": "",
    "CompanyGstinSap": "",
    "VendorName": "",
    "VendorGstin": "",
    "CVendorGstin": "",
    "InvoiceNo": "",
    "CInvoiceNo": "",
    "InvoiceDate": "",
    "CInvoiceDate": "",
    "InvoiceAmount": "",
    "CInvoiceAmount": "",
    "PoLpoIoNoPdf": "",
    "CPoLpoIoNo": "",
    "IrnNo": "",
    "CIrnNo": "",
    "MsmeNo": "",
    "Status": "Draft",
    "ModeOfEntry": "Manual",
    "CreatedOn": "",
    "CreatedBy": "",
    "ChangedOn": "",
    "ChangedBy": "",
    "FileName": "",
    "ErrorNo": "",
    "ErrorMsg": "",
    "ErrorType": "",
    "Flag": "A",
    "DCCHEADERTODCCSES": []
}


# === RETRY DECORATOR ===
def retry_with_backoff(max_retries=5, backoff_factor=2, allowed_exceptions=(Exception,)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = 1
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(f"❌ {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    sleep_time = delay + random.uniform(0, 0.5)  # jitter
                    logger.warning(f"⚠️ {func.__name__} error: {e} → retrying in {sleep_time:.1f}s (attempt {attempt+1})")
                    time.sleep(sleep_time)
                    delay *= backoff_factor
        return wrapper
    return decorator


# === STEP 1: AZURE OCR EXTRACTION ===
@retry_with_backoff(max_retries=3, allowed_exceptions=(requests.RequestException,))
def azure_extract_text(pdf_file):
    if not os.path.exists(pdf_file):
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    endpoint = os.getenv("AZURE_ENDPOINT")
    key = os.getenv("AZURE_API_KEY")

    if not endpoint or not key:
        raise EnvironmentError("Azure Document Intelligence credentials missing.")

    try:
        client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        with open(pdf_file, "rb") as f:
            poller = client.begin_analyze_document(model_id="prebuilt-read", body=f)
        result = poller.result()

        text_lines, extracted_words = [], {}
        doc = fitz.open(pdf_file)

        for page in result.pages:
            text_lines.extend(line.content for line in page.lines)
            pymupdf_page = doc[page.page_number - 1]
            page_width, page_height = pymupdf_page.rect.width, pymupdf_page.rect.height

            for word in page.words:
                xs, ys = word.polygon[0::2], word.polygon[1::2]
                x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
                value = [page.page_number, x, y, w, h, page_width, page_height]
                extracted_words.setdefault(word.content, []).append(value)

        logger.info(f"✅ Extracted {len(text_lines)} lines from {pdf_file}")
        return {"status": True, "text": "\n".join(text_lines), "cordinates": extracted_words}

    except Exception as e:
        logger.error(f"❌ Azure OCR failed for {pdf_file}: {e}")
        return {"status": False, "error": str(e)}


# === STEP 2: FORMAT WITH LLM ===
@retry_with_backoff(max_retries=3, allowed_exceptions=(requests.RequestException,))
def format_with_llm(text):
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not endpoint or not key or not deployment:
        raise EnvironmentError("Azure OpenAI credentials missing.")

    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-01"
        )

        prompt = f"""
        You are an information extraction system. Extract invoice fields into strict JSON:
        (Schema omitted here for brevity – use your schema.)
        Raw text:
        {text}
        """

        response = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": "Return only valid JSON."},
                      {"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0
        )

        content = response.choices[0].message.content
        parsed_data = json.loads(content)
        logger.info("🤖 LLM returned valid JSON")
        return {"status": True, "json": parsed_data}

    except json.JSONDecodeError as e:
        logger.error(f"❌ LLM returned invalid JSON: {e}")
        return {"status": False, "error": "Invalid JSON response"}
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}")
        return {"status": False, "error": str(e)}


# === STEP 3: BUILD FINAL JSON ===
def final_json(json_input):
    try:
        sap_json = SAP_JSON_TEMPLATE.copy()
        sap_json["FileName"] = json_input.get("file", "")

        # Example mapping (add full logic as needed)
        data = json_input.get("data", {})
        sap_json["InvoiceNo"] = data.get("InvoiceNo", "")
        sap_json["InvoiceDate"] = data.get("InvoiceDate", "").replace("-", "")
        sap_json["InvoiceAmount"] = data.get("InvoiceAmount", "")

        logger.info("📦 Final SAP JSON built")
        return {"status": True, "data": sap_json}

    except Exception as e:
        logger.error(f"❌ Failed in final_json: {e}")
        return {"status": False, "error": str(e)}


# === STEP 4: FULL PIPELINE PER PDF ===
def process_pdf(pdf_file):
    logger.info(f"🚀 Processing {pdf_file}")
    try:
        result_azure = azure_extract_text(pdf_file)
        if not result_azure.get("status"):
            return {"success": False, "error": result_azure.get("error", "Azure OCR failed")}

        result_llm = format_with_llm(result_azure["text"])
        if not result_llm.get("status"):
            return {"success": False, "error": result_llm.get("error", "LLM failed")}

        result_final = final_json({
            "data": result_llm["json"],
            "text": result_azure["text"],
            "cordinates": result_azure["cordinates"],
            "file": os.path.basename(pdf_file)
        })

        if not result_final.get("status"):
            return {"success": False, "error": result_final.get("error", "Final JSON failed")}

        return {"success": True, "data": result_final["data"]}

    except Exception as e:
        logger.exception(f"Unhandled error in process_pdf for {pdf_file}: {e}")
        return {"success": False, "error": str(e)}


# === STEP 5: MULTI-PDF PIPELINE ===
def process_pdfs(folder_path, max_workers=3):
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Invalid folder path: {folder_path}")

    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        logger.warning("⚠️ No PDFs found in folder")
        return []

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {executor.submit(process_pdf, pdf): pdf for pdf in pdf_files}
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_name = future_to_pdf[future]
            try:
                results.append(future.result())
            except Exception as e:
                logger.exception(f"Unhandled exception for {pdf_name}: {e}")
                results.append({"success": False, "error": str(e)})
    return results


# === MAIN ===
if __name__ == "__main__":
    folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\test"
    final_results = process_pdfs(folder_path, max_workers=3)

    print("\n=== Final Results ===")
    for r in final_results:
        print(json.dumps(r, indent=2))
