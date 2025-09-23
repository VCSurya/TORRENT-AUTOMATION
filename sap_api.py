import requests
import urllib3

# 🔕 Disable SSL warnings (only for dev/test, not production!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SAP URLs ---
BASE_URL = "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV"
POST_URL = f"{BASE_URL}/ZFI_DCC_HEADERSet"
# For CSRF token fetch, root or entityset is enough (no $expand needed)
TOKEN_URL = f"{BASE_URL}/"

# --- SAP Credentials ---
SAP_USERNAME = "111440"   # 🔑 put your SAP username
SAP_PASSWORD = "Dev@1234"   # 🔑 put your SAP password


def send_data_to_sap(data):
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
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-csrf-token": csrf_token
    }

    response = session.post(
        POST_URL,
        json=data,
        headers=headers,
        auth=(SAP_USERNAME, SAP_PASSWORD),
        cookies=cookies,
        verify=False
    )

    # --- Step 3: Handle Response ---
    if response.status_code in [200, 201]:
        print("✅ Data sent to SAP successfully")
        print("Response:", response.json())
        return response.status_code, response.json()
    else:
        print("❌ Failed to send data")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        return response.status_code, None


# --- Example Payload ---
data = {
    "InwardRefNo": "",
    "SourceOfDoc": "",
    "DocMailPerson": "",
    "InwardDate": "",
    "PoLpo": "",
    "GaName": "",
    "CompanyGstinPdf": "08AAHCD1012H1Z4",
    "CCompanyGstinPdf": "1,111.08,218.56,165.36,225.45",
    "CompanyGstinSap": "",
    "VendorName": "",
    "VendorGstin": "27AAJCG7930M1Z1",
    "CVendorGstin": "",
    "InvoiceNo": "GGPL2526/242",
    "CInvoiceNo": "1,415.79,219.65,463.95,227.00",
    "InvoiceDate": "20250830",
    "CInvoiceDate": "",
    "InvoiceAmount": "254880.00",
    "CInvoiceAmount": "",
    "PoLpoIoNoPdf": "34000773",
    "CPoLpoIoNo": "",
    "IrnNo": "bb2547493c01d23694118ff858500b9c6efe1f540e48a4ff7b7d508dd68647",
    "CIrnNo": "",
    "MsmeNo": "",
    "Status": "Draft",
    "ModeOfEntry": "Manual",
    "CreatedOn": "20250910",
    "CreatedBy": "DEVESH",
    "ChangedOn": "20250918",
    "ChangedBy": "DEVESH",
    "FileName": "3780_001.pdf",
    "ErrorNo": "",
    "ErrorMsg": "",
    "ErrorType": "S",
    "Flag": "A",
    "DCCHEADERTODCCSES": [
        {
            "InwardRefNo": "",
            "PoNo": "34000773",
            "SesGrnScrollNoPdf": "5000180487",
            "ItemNo": "1",
            "SesGrnScrollNoSap": "",
            "ParkDocNo": "",
            "Amount": "254880.00",
            "CreatedOn": "20250910",
            "Zindicator": "",
            "CreatedBy": "DEVESH",
            "CSesGrnScrollNoPdf": "1,136.12,571.41,267.57,586.95",
            "ChangedOn": "20250918",
            "ChangedBy": "DEVESH"
        }
    ]
}

if __name__ == "__main__":
    send_data_to_sap(data)


# {'d': {'__metadata': {'id': "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/ZFI_DCC_HEADERSet('0000000023')", 'uri': "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/ZFI_DCC_HEADERSet('0000000023')", 'type': 'ZFI_DCC_PORTAL_SRV.ZFI_DCC_HEADER'}, 'InwardRefNo': '0000000023', 'SourceOfDoc': '', 'DocMailPerson': '', 'InwardDate': '', 'PoLpo': '', 'GaName': '', 'CompanyGstinPdf': '08AAHCD1012H1Z4', 'CCompanyGstinPdf': '1,111.08,218.56,165.36,225.45', 'CompanyGstinSap': '', 'VendorName': '', 'VendorGstin': '27AAJCG7930M1Z1', 'CVendorGstin': '', 'InvoiceNo': 'GGPL2526/242', 'CInvoiceNo': '1,415.79,219.65,463.95,227.00', 'InvoiceDate': '20250830', 'CInvoiceDate': '', 'InvoiceAmount': '254880.00', 'CInvoiceAmount': '', 'PoLpoIoNoPdf': '34000773', 'CPoLpoIoNo': '', 'IrnNo': 'bb2547493c01d23694118ff858500b9c6efe1f540e48a4ff7b7d508dd68647', 'CIrnNo': '', 'MsmeNo': '', 'VendorCode': '', 'CompanyCode': '', 'Status': 'Draft', 'ModeOfEntry': 'Manual', 'CreatedOn': '20250910', 'CreatedBy': 'DEVESH', 'ChangedOn': '20250918', 'ChangedBy': 'DEVESH', 'FileName': '3780_001.pdf', 'ErrorNo': '', 'ErrorMsg': '', 'ErrorType': 'S', 'Flag': 'A', 'GaCode': '', 'Invoicedocnumber': '', 'Fiscalyear': '0000', 'DCCHEADERTODCCSES': {'results': [{'__metadata': {'id': "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/ZFI_DCC_SESSet('')", 'uri': "https://tgps4hdevapp.torrentgas.com:8240/sap/opu/odata/sap/ZFI_DCC_PORTAL_SRV/ZFI_DCC_SESSet('')", 'type': 'ZFI_DCC_PORTAL_SRV.ZFI_DCC_SES'}, 'InwardRefNo': '', 'PoNo': '34000773', 'ItemNo': '1', 'SesGrnScrollNoPdf': '5000180487', 'ParkDocNo': '', 'SesGrnScrollNoSap': '', 'Amount': '254880.00', 'CreatedOn': '20250910', 'CreatedBy': 'DEVESH', 'Zindicator': '', 'ChangedOn': '20250918', 'CSesGrnScrollNoPdf': '1,136.12,571.41,267.57,586.95', 'ChangedBy': 'DEVESH'}]}}}