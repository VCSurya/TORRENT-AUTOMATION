import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_pdf(pdf_path, endpoint, key):
    try:
        # Create client
        client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # Open PDF and send it to Azure
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-read",
                body=f,
                content_type="application/pdf"
            )

        result = poller.result()

        # Extract all text
        text = []
        for page in result.pages:
            for line in page.lines:
                text.append(line.content)

        return "\n".join(text)

    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {str(e)}")
        return None


if __name__ == "__main__":
    endpoint = os.getenv("AZURE_ENDPOINT")
    key = os.getenv("AZURE_API_KEY")

    pdf_path = r"C:\Users\111439\Downloads\safepdfkit (1).pdf"

    extracted_text = extract_text_from_pdf(pdf_path, endpoint, key)

    if extracted_text:
       
        with open('out.txt', "w", encoding="utf-8") as out_file:
            out_file.write(extracted_text)

        # print(f"✅ Saved: {txt_path}")
    
    # else:
    #     print(f"⚠️ Skipped: {file_name}")
    # input_folder = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs"
    # output_folder = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\all_pdfs_extracted_text"

    # # Create output folder if not exists
    # os.makedirs(output_folder, exist_ok=True)

    # for file_name in os.listdir(input_folder):
    #     if file_name.lower().endswith(".pdf"):
    #         pdf_path = os.path.join(input_folder, file_name)
    #         print(f"📄 Processing: {pdf_path}")

    #         extracted_text = extract_text_from_pdf(pdf_path, endpoint, key)

    #         if extracted_text:
    #             txt_name = os.path.splitext(file_name)[0] + ".txt"
    #             txt_path = os.path.join(output_folder, txt_name)

    #             with open(txt_path, "w", encoding="utf-8") as out_file:
    #                 out_file.write(extracted_text)

    #             print(f"✅ Saved: {txt_path}")
    #         else:
    #             print(f"⚠️ Skipped: {file_name}")
