import requests
import urllib3
import base64

# 🔕 Disable SSL warnings (for dev/test only)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SAP URLs ---
SAP_URL = "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/ZFI_DCC_HEADERSet?$expand=DCCHEADERTODCCSES&$format=json"

# SAP_URL = "https://s4hanaap.vc-erp.com:44320/sap/opu/odata/SAP/ZCOTTON_BALE_MANAGEMENT_SYSTEM_SRV/inv_headSet?$expand=InvHederTOItem&$format=json"


# --- SAP Credentials ---
SAP_USERNAME = "111440"
SAP_PASSWORD = "Test@1234"


# Example payload to send

# Start a session for cookies and CSRF handling
session = requests.Session()

# Step 1: Fetch CSRF Token
token_response = session.get(
    SAP_URL,
    auth=(SAP_USERNAME, SAP_PASSWORD),
    headers={"x-csrf-token": "Fetch"},
    verify=False
)

csrf_token = token_response.headers.get("x-csrf-token")
cookies = token_response.cookies

print(cookies)

if token_response.status_code != 200:
    print("Failed to fetch CSRF token")
    # print("Response:", token_response.text)


csrf_token = token_response.headers.get("x-csrf-token")
cookies = token_response.cookies

# Step 2: Send actual data
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "x-csrf-token": csrf_token
}



