from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()
def extract_words_with_coords_from_pdf(pdf_path, endpoint, key, output_txt_path):
    try:
        # Create client
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # Open PDF and send to Azure
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-read",
                document=f
            )

        result = poller.result()

        # Extract all text
        text = []
        for page in result.pages:
            for line in page.lines:
                text.append(line.content)

        TEXT = "\n".join(text)

        extracted_words = []

        for page in result.pages:
            for word in page.words:
                bbox = word.polygon
                xs = [point.x for point in bbox]
                ys = [point.y for point in bbox]

                x = min(xs)
                y = min(ys)
                width = max(xs) - x
                height = max(ys) - y

                extracted_words.append({
                    "text": word.content,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "page_number": page.page_number
                })


        # # Write to output text file
        # with open(output_txt_path, "w", encoding="utf-8") as out_file:
        # Page,X,Y,Height,Width
        word_dimentions = {}
        
        for word_info in extracted_words:
            word_dimentions[word_info['text']] = [
                word_info['page_number'],
                round(word_info['x'], 2),
                round(word_info['y'], 2),
                round(word_info['height'], 2),
                round(word_info['width'] + 0.4, 2)
            ]

            # f"Page {word_info['page_number']} | "
            # f"Text: {word_info['text']} | "
            # f"x: {word_info['x']:.2f}, y: {word_info['y']:.2f}, "
            # f"width: {word_info['width']+0.4:.2f}, height: {word_info['height']:.2f}\n"
            

        print(f"✅ Extraction complete!")

    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {str(e)}")


if __name__ == "__main__":
    # Replace these with your actual values
    PDF_PATH = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\5876.25-26.pdf"
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    AZURE_KEY = os.getenv("AZURE_API_KEY")
    OUTPUT_TXT_PATH = "extracted_words_with_coords.txt"

    extract_words_with_coords_from_pdf(PDF_PATH, AZURE_ENDPOINT, AZURE_KEY, OUTPUT_TXT_PATH)
