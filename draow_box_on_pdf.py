# from azure.ai.formrecognizer import DocumentAnalysisClient
# from azure.core.credentials import AzureKeyCredential
# from dotenv import load_dotenv
# import os
# import fitz  # PyMuPDF

# load_dotenv()


# def extract_words_with_coords_from_pdf(pdf_path, endpoint, key, output_txt_path=None):
#     try:
#         client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

#         with open(pdf_path, "rb") as f:
#             poller = client.begin_analyze_document(
#                 model_id="prebuilt-read",
#                 document=f
#             )

#         result = poller.result()

#         extracted_words = []

#         for page in result.pages:
#             for word in page.words:
#                 bbox = word.polygon  # Use polygon for word
#                 xs = [point.x for point in bbox]
#                 ys = [point.y for point in bbox]

#                 x = min(xs)
#                 y = min(ys)
#                 width = max(xs) - x
#                 height = max(ys) - y

#                 extracted_words.append({
#                     "text": word.content,
#                     "x": x,
#                     "y": y,
#                     "width": width,
#                     "height": height,
#                     "page_number": page.page_number
#                 })

#         # Optional: Save to .txt
#         if output_txt_path:
#             with open(output_txt_path, "w", encoding="utf-8") as out_file:
#                 for word_info in extracted_words:
#                     out_file.write(
#                         f"Page {word_info['page_number']} | "
#                         f"Text: {word_info['text']} | "
#                         f"x: {word_info['x']:.2f}, y: {word_info['y']:.2f}, "
#                         f"width: {word_info['width']:.2f}, height: {word_info['height']:.2f}\n"
#                     )

#         return extracted_words

#     except Exception as e:
#         print(f"❌ Error processing {pdf_path}: {str(e)}")
#         return []


# def draw_boxes_on_pdf(pdf_path, word_data, output_pdf_path):
#     doc = fitz.open(pdf_path)

#     for word in word_data:
#         page_number = word["page_number"] - 1  # Azure is 1-based, PyMuPDF is 0-based
#         page = doc.load_page(page_number)

#         page_width = page.rect.width
#         page_height = page.rect.height

#         # Convert normalized to absolute
#         x = word["x"] * page_width
#         y = word["y"] * page_height
#         width = word["width"] * page_width
#         height = word["height"] * page_height

#         # Flip Y-axis (top-left to bottom-left)
#         y = page_height - y - height

#         rect = fitz.Rect(x, y, x + width, y + height)
#         page.draw_rect(rect, color=(1, 0, 0), width=0.5)  # Red box

#     doc.save(output_pdf_path)
#     doc.close()
#     print(f"✅ Output PDF with boxes saved to: {output_pdf_path}")


# if __name__ == "__main__":
#     # Load from .env or hardcode
#     AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
#     AZURE_KEY = os.getenv("AZURE_API_KEY")

#     PDF_PATH = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\3780_001.pdf"
#     OUTPUT_TXT_PATH = "extracted_words.txt"
#     OUTPUT_PDF_PATH = "output_with_boxes.pdf"

#     # Step 1: Extract words with coordinates
#     word_data = extract_words_with_coords_from_pdf(PDF_PATH, AZURE_ENDPOINT, AZURE_KEY, OUTPUT_TXT_PATH)

#     # Step 2: Draw boxes and save new PDF
#     draw_boxes_on_pdf(PDF_PATH, word_data, OUTPUT_PDF_PATH)

import fitz  # PyMuPDF

# (1193.687317767334, -2372.117197741699, 1830.07026751709, -2254.7040130615233)
# [1, 2.0031, 3.675, 1.0679000000000003, 0.13929999999999998, 595.9199829101562, 842.8800048828125]

pdf_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\5876.25-26.pdf"
output_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\5876.25-26_bbox.pdf"

# Open PDF
doc = fitz.open(pdf_path)

[1, 2.0031, 3.675, 1.0679000000000003, 0.13929999999999998, 595.9199829101562, 842.8800048828125]
# Example bbox info (values in inches)
bbox_info = {
    "page": 0,  # page index (0-based)
    "x": 2.0031,      # inches from left
    "y": 3.675,      # inches from top
    "width": 1.0679000000000003,  # inches
    "height":  0.13929999999999998, # inches
    "text": ""
}


page = doc[bbox_info["page"]]

# Convert inches to points (1 inch = 72 points)
x0 = bbox_info["x"] * 72
y0 = bbox_info["y"] * 72
x1 = x0 + bbox_info["width"] * 72
y1 = y0 + bbox_info["height"] * 72
print(x0, y0, x1, y1)
# Make rectangle
bbox_rect = fitz.Rect(x0, y0, x1, y1)

# Draw rectangle (red outline)
page.draw_rect(bbox_rect, color=(1, 0, 0), width=1)

# Add text label above the box
page.insert_text((x0, y0 - 10), bbox_info["text"], fontsize=8, color=(0, 0, 1))

# Save new PDF
doc.save(output_path)
doc.close()

print(f"✅ BBox drawn and saved to {output_path}")
