from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Directory to save text files
TEXT_DIR = "text_dir"

# Ensure the directory exists
if not os.path.exists(TEXT_DIR):
    os.makedirs(TEXT_DIR)

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
