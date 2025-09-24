from flask import Flask, request, jsonify
import os
import base64
from main import process_pdf
app = Flask(__name__)

# Directory to save text files
TEXT_DIR = "text_dir"

# Ensure the directory exists
if not os.path.exists(TEXT_DIR):
    os.makedirs(TEXT_DIR)

# Directory where PDFs will be stored
PDF_SAVE_DIR = "uploaded_pdfs"
os.makedirs(PDF_SAVE_DIR, exist_ok=True)

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        data = request.get_json()

        pdf_name = data.get("pdf_name")
        pdf_base64 = data.get("pdf_base64")

        if not pdf_name or not pdf_base64:
            return jsonify({"error": "Missing 'pdf_name' or 'pdf_base64'"}), 400

        # Ensure .pdf extension
        if not pdf_name.lower().endswith(".pdf"):
            pdf_name += ".pdf"

        # Decode base64 string
        pdf_bytes = base64.b64decode(pdf_base64)

        # Save file
        file_path = os.path.join(PDF_SAVE_DIR, pdf_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Print full path in logs
        print("PDF saved at:", os.path.abspath(file_path))

        result = process_pdf(os.path.abspath(file_path))

        # Return result directly
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/save_text', methods=['POST'])
def save_text():
    try:
        data = request.get_json()

        pdf_name = data.get('pdf_name')
        text = data.get('text')

        if not pdf_name or not text:
            return jsonify({
                "success": False,
                "error": "Missing 'pdf_name' or 'text' in request."
            }), 400

        # Define the path where the text file will be saved
        file_path = os.path.join(TEXT_DIR, f"{pdf_name}.txt")

        # Write the text to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text)

        return jsonify({
            "success": True,
            "msg": "Text saved successfully.",
            "pdf_name": pdf_name
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "pdf_name": data.get('pdf_name', 'unknown')
        }), 500

@app.route('/', methods=['GET'])
def main():
    return {'status':True,'msg':"API Is Running..."}


if __name__ == '__main__':
    app.run(debug=True)
