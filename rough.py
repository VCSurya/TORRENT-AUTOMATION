import requests
import urllib3
from urllib.parse import urljoin

# --- disable insecure request warnings (only for dev/test) ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SAP Credentials & connection settings ---
SAP_USERNAME = "111440"
SAP_PASSWORD = "Test@1234"

# Base service URL (scheme + host + optional port + base path to OData service)
SAP_BASE_URL = "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/"

# Specify the OData entity (set) you want to call
SAP_ENTITY = "AttachmentSet"

# Specify the sap client
SAP_CLIENT = "335"   # change to your client number

# Optional OData query params (example from your original URL)
params = {
    "$expand": "DCCHEADERTODCCSES",
    "$format": "json"
    # If you prefer, you can add "sap-client": SAP_CLIENT here as a query param,
    # but sending sap-client in headers is typically used.
}

# Session and headers
session = requests.Session()
headers = {
    "x-csrf-token": "Fetch",
    "Accept": "application/json",
    "sap-client": SAP_CLIENT
}

# Build full URL for the entity
request_url = urljoin(SAP_BASE_URL, SAP_ENTITY)

try:
    token_response = session.get(
        request_url,
        auth=(SAP_USERNAME, SAP_PASSWORD),
        headers=headers,
        verify=False  # remove or set to True in production with proper certs
    )
except requests.RequestException as e:
    print("❌ Request failed:", e)
else:
    status = token_response.status_code
    if status != 200:
        print(f"❌ Failed to fetch CSRF token (status {status})")
        print("Response text (truncated):", token_response.text)
    else:
        csrf_token = token_response.headers.get("x-csrf-token")
        cookies = token_response.cookies
        print("✅ CSRF Token fetched:", csrf_token)
        print("Cookies returned:", cookies.get_dict())
        # If you want, inspect the returned JSON metadata/payload
        try:
            data = token_response.json()
            # show a short summary
            if isinstance(data, dict):
                print("Top-level keys in JSON:", list(data.keys()))
            else:
                print("Response JSON type:", type(data))
        except ValueError:
            print("Response is not valid JSON.")
