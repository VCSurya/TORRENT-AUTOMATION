import fitz  # PyMuPDF

# (1193.687317767334, -2372.117197741699, 1830.07026751709, -2254.7040130615233)
# [1, 2.0031, 3.675, 1.0679000000000003, 0.13929999999999998, 595.9199829101562, 842.8800048828125]

pdf_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Documents\FW_ Invoice Copies\RA-02 Auraiya.pdf"
output_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\5876.25-26_bbox.pdf"

# Open PDF
doc = fitz.open(pdf_path)

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
bbox_rect = fitz.Rect(99.78,482.26,153.00,491.90)

# Draw rectangle (red outline)
page.draw_rect(bbox_rect, color=(1, 0, 0), width=1)

# Add text label above the box
page.insert_text((x0, y0 - 10), bbox_info["text"], fontsize=8, color=(0, 0, 1))

# Save new PDF
doc.save(output_path)
doc.close()

print(f"✅ BBox drawn and saved to {output_path}")
