import requests
import urllib3
import base64

# 🔕 Disable SSL warnings (for dev/test only)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SAP URLs ---
BASE_URL = "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV"
ATTACHMENT_URL = f"{BASE_URL}/AttachmentSet"
TOKEN_URL = f"{BASE_URL}/"

# --- SAP Credentials ---
SAP_USERNAME = "111440"
SAP_PASSWORD = "Dev@1234"

def extract_file_name(xml_text):
    start_tag = "<d:FileName>"
    end_tag = "</d:FileName>"

    start_index = xml_text.find(start_tag)
    if start_index == -1:
        return None  # FileName tag not found

    start_index += len(start_tag)
    end_index = xml_text.find(end_tag, start_index)
    if end_index == -1:
        return None  # Closing tag not found

    return xml_text[start_index:end_index]

def send_pdf_to_sap(pdf_path):

    # Read PDF and convert to Base64
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    session = requests.Session()

    # --- Step 1: Fetch CSRF Token ---
    token_response = session.get(
        TOKEN_URL,
        auth=(SAP_USERNAME, SAP_PASSWORD),
        headers={"x-csrf-token": "Fetch"},
        verify=False
    )

    if token_response.status_code != 200:
        print("❌ Failed to fetch CSRF token")
        print("Status:", token_response.status_code)
        print("Response:", token_response.text)
        return None

    csrf_token = token_response.headers.get("x-csrf-token")
    cookies = token_response.cookies
    print("✅ CSRF Token fetched:", csrf_token)

    # --- Step 2: Send POST request with CSRF token ---
    headers = {
        "Content-Type": "application/pdf",
        # "Accept": "application/json",
        "x-csrf-token": csrf_token,
        "Slug": '1000000022_S_Test.pdf'
    }

    response = session.post(
        ATTACHMENT_URL,
        data=pdf_base64,
        headers=headers,
        auth=(SAP_USERNAME, SAP_PASSWORD),
        cookies=cookies,
        verify=False
    )

    # --- Step 3: Handle Response ---
    if response.status_code in [200, 201]:
        print("✅ PDF sent to SAP successfully")
        print("Response:", response)
        return extract_file_name(response.text)
        # return (response.status_code, response.text)
    else:
        print("❌ Failed to send PDF")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        return (response.status_code, None)

# --- Example Usage ---
if __name__ == "__main__":
    pdf_file_path = r"C:\Users\111439\Downloads\Test PDF 123.pdf"
    inward_ref_no = "0000000023"  # Use the InwardRefNo returned from your header POST
    result = send_pdf_to_sap(pdf_file_path)
    print('👌',result)
