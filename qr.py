from pdf2image import convert_from_path
import cv2
import numpy as np
import os


def crop_qr_opencv(pdf_path, output_folder="output_qr", dpi=300):
    os.makedirs(output_folder, exist_ok=True)

    # Convert PDF to images
    pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\poppler-24.08.0\Library\bin")

    qr_detector = cv2.QRCodeDetector()
    qr_count = 0

    for page_num, page in enumerate(pages, start=1):
        # Convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)

        # Works for OpenCV >= 4.7
        retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(img)

        if points is None:
            print(f"⚠️ No QR found on page {page_num}")
            continue

        for i, box in enumerate(points):
            # Convert float points to int
            pts = box.astype(int)
            x_min, y_min = pts[:, 0].min(), pts[:, 1].min()
            x_max, y_max = pts[:, 0].max(), pts[:, 1].max()

            # Crop QR
            qr_crop = img[y_min:y_max, x_min:x_max]
            qr_filename = os.path.join(output_folder, f"page{page_num}_qr{i+1}.png")
            cv2.imwrite(qr_filename, qr_crop)
            print(f"✅ Saved {qr_filename}")
            qr_count += 1

    if qr_count == 0:
        print("❌ No QR codes found in the entire PDF.")
    else:
        print(f"🎉 Extracted {qr_count} QR code(s).")


# Example usage
crop_qr_opencv(r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\einv1 - 2025-09-10T173713.406 (1).pdf")