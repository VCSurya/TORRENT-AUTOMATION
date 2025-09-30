from flask import Flask, request, jsonify
import os
import base64
from main import process_pdf
from flask_cors import  CORS
import json

app = Flask(__name__)

CORS(app)

# Directory to save text files
TEXT_DIR = "text_dir"
RESULT_DIR = "result"

# Ensure the directory exists
if not os.path.exists(TEXT_DIR):
    os.makedirs(TEXT_DIR)

# Ensure the directory exists
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)

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
            return jsonify({"Error":0,"Error Msg": "Missing 'pdf_name' or 'pdf_base64'"}), 400

        # Ensure .pdf extension
        if not pdf_name.lower().endswith(".pdf"):
            pdf_name += ".pdf"

        # Decode base64 string
        pdf_bytes = base64.b64decode(pdf_base64)

        # Save file
        file_path = os.path.join(PDF_SAVE_DIR, pdf_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
    
        result = process_pdf(os.path.abspath(file_path))

        print(result.get('json') if result.get('json') else "")

        if os.path.exists(os.path.abspath(file_path)):
            os.remove(os.path.abspath(file_path))
        
        ### Note: if success is X means true and "" means false

        if result['status']:
            return jsonify({'success':'X','InwardRefNo':result.get('no')}), 200

        else:
            return jsonify({'success':"",'InwardRefNo':result.get('no') if result.get('no') else "",'error':result.get('error') if result.get('error') else ""}), 501
        
    except Exception as e:
        return jsonify({'success':"","error": str(e)}), 500


@app.route('/', methods=['GET'])
def main():
    return {"msg":"API Is Running..."}

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000,debug=True)
