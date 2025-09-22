from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()


def extract_words_with_coords_from_pdf(pdf_path, endpoint, key, output_txt_path=None):
    try:
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-read",
                document=f
            )

        result = poller.result()

        extracted_words = []

        for page in result.pages:
            for word in page.words:
                bbox = word.polygon  # Use polygon for word
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

        # Optional: Save to .txt
        if output_txt_path:
            with open(output_txt_path, "w", encoding="utf-8") as out_file:
                for word_info in extracted_words:
                    out_file.write(
                        f"Page {word_info['page_number']} | "
                        f"Text: {word_info['text']} | "
                        f"x: {word_info['x']:.2f}, y: {word_info['y']:.2f}, "
                        f"width: {word_info['width']:.2f}, height: {word_info['height']:.2f}\n"
                    )

        return extracted_words

    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {str(e)}")
        return []


def draw_boxes_on_pdf(pdf_path, word_data, output_pdf_path):
    doc = fitz.open(pdf_path)

    for word in word_data:
        page_number = word["page_number"] - 1  # Azure is 1-based, PyMuPDF is 0-based
        page = doc.load_page(page_number)

        page_width = page.rect.width
        page_height = page.rect.height

        # Convert normalized to absolute
        x = word["x"] * page_width
        y = word["y"] * page_height
        width = word["width"] * page_width
        height = word["height"] * page_height

        # Flip Y-axis (top-left to bottom-left)
        y = page_height - y - height

        rect = fitz.Rect(x, y, x + width, y + height)
        page.draw_rect(rect, color=(1, 0, 0), width=0.5)  # Red box

    doc.save(output_pdf_path)
    doc.close()
    print(f"✅ Output PDF with boxes saved to: {output_pdf_path}")


if __name__ == "__main__":
    # Load from .env or hardcode
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    AZURE_KEY = os.getenv("AZURE_API_KEY")

    PDF_PATH = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\3780_001.pdf"
    OUTPUT_TXT_PATH = "extracted_words.txt"
    OUTPUT_PDF_PATH = "output_with_boxes.pdf"

    # Step 1: Extract words with coordinates
    word_data = extract_words_with_coords_from_pdf(PDF_PATH, AZURE_ENDPOINT, AZURE_KEY, OUTPUT_TXT_PATH)

    # Step 2: Draw boxes and save new PDF
    draw_boxes_on_pdf(PDF_PATH, word_data, OUTPUT_PDF_PATH)
