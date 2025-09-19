import fitz  # PyMuPDF

def is_digital_pdf(pdf_path, text_threshold=0.1):
    """
    Determines whether a PDF is digital (contains selectable text)
    or scanned (image-only).
    
    Args:
        pdf_path (str): Path to the PDF file.
        text_threshold (float): Minimum fraction of pages that must contain text to be considered digital.
        
    Returns:
        bool: True if digital, False if scanned.
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_with_text = 0

        for page in doc:
            text = page.get_text()
            if text.strip():
                pages_with_text += 1

        doc.close()

        # If a significant portion of pages contain text, it's likely digital
        if pages_with_text / total_pages >= text_threshold:
            return True  # Digital
        else:
            return False  # Scanned

    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False
    

# pdf_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\3780_001.pdf" # scanned pdf
pdf_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\5876.25-26.pdf" # scanned pdf

if is_digital_pdf(pdf_path):
    print("The PDF is digital (contains selectable text).")
else:
    print("The PDF is scanned (image-based).")
