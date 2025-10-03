from flask import Flask, request, jsonify,render_template
import os
import base64
from main import process_pdf
from flask_cors import  CORS
from jinja2 import Template
import json, ast
import ssl
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

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

def generate_temp_cert():
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        return

    # Generate private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Write private key
    with open("key.pem", "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    # Generate self-signed certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"TempCert"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=1)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    ).sign(key, hashes.SHA256())

    # Write certificate
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("Temporary self-signed certificate generated.")

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        data = request.get_json()

        pdf_name = data.get("pdf_name", "")
        pdf_base64 = data.get("pdf_base64", "")
        Mode_Of_Entry = data.get("mode_of_entry", "")
        Created_On = data.get("created_on", "")
        Created_By = data.get("created_by", "")

        
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
    
        result = process_pdf(os.path.abspath(file_path),Mode_Of_Entry,Created_On,Created_By)

        if os.path.exists(os.path.abspath(file_path)):
            os.remove(os.path.abspath(file_path))
        
        ### Note: if success is X means true and "" means false

        if result['status']:
            return jsonify({'success':'X','InwardRefNo':result.get('no')}), 200

        else:
            return jsonify({'success':"",'InwardRefNo':result.get('no') if result.get('no') else "",'error':result.get('error') if result.get('error') else ""}), 501
        
    except Exception as e:
        return jsonify({'success':"","error": str(e)}), 500

@app.route('/help', methods=['GET'])
def help():

    # Load data
    with open("latest/latest_pdf_azure_text.txt",'r',encoding='utf-8') as file:
        TEXT = file.read()

    with open("latest/latest_pdf_azure_text_cordinates.json", 'r', encoding='utf-8') as file:
        WORD_CORDINATES = json.dumps(json.load(file), indent=2)

    with open("latest/latest_pdf_output.json", 'r', encoding='utf-8') as file:
        FINAL_JSON = json.dumps(json.load(file), indent=2)

    with open("latest/latest_pdf_logs.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        LOGS = ast.literal_eval(content)  # Safely parse string to list
        LOGS = json.dumps(LOGS, indent=2)  # Format nicely for HTML

    with open("latest/latest_pdf_open_ai_respons.txt", 'r', encoding='utf-8') as file:
        OPEN_AI_RESPONS = file.read()

    with open("prompt.txt", 'r', encoding='utf-8') as file:
        PROMPT_TEMPLATE = file.read()

    return render_template('help.html',
                           TEXT=TEXT,
                           WORD_CORDINATES=WORD_CORDINATES,
                           FINAL_JSON=FINAL_JSON,
                           LOGS=LOGS,
                           OPEN_AI_RESPONS=OPEN_AI_RESPONS,
                           PROMPT_TEMPLATE=PROMPT_TEMPLATE)


@app.route('/edit-prompt', methods=['POST'])
def edit_prompt():
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing "prompt" in request body'}), 400

        prompt_text = data['prompt']

        with open('prompt.txt', 'w', encoding='utf-8') as f:
            f.write(prompt_text)

        return jsonify({'message': 'Prompt saved successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def main():
    return {"msg":"API Is Running..."}

if __name__ == '__main__':
    generate_temp_cert()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')

    # Run Flask over HTTPS
    app.run(host='0.0.0.0', port=5000, ssl_context=context)
    # app.run(host="0.0.0.0",port=5000,debug=True)
