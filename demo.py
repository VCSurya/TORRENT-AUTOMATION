import os
# import PyPDF2

# def read_pdfs_from_folder(folder_path):
#     # Get all PDF files from folder, sorted alphabetically
#     pdf_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")])

#     for pdf_file in pdf_files:
#         file_path = os.path.join(folder_path, pdf_file)
#         print(f"\n=== Reading: {pdf_file} ===\n")

#         # Open the PDF
#         with open(file_path, "rb") as f:
#             reader = PyPDF2.PdfReader(f)

#             # Loop through pages
#             for page_num, page in enumerate(reader.pages, start=1):
#                 text = page.extract_text()
#                 print(f"--- Page {page_num} ---")
#                 print(text if text else "[No extractable text]")

# # Example usage
# folder_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\FW__Invoice_Copies"  # change this path
# read_pdfs_from_folder(folder_path)

