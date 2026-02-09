import os
import httpx
import traceback
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# MAKE CONNECTION FOR TLS handshake
timeout = httpx.Timeout(connect=45.0, read=30.0,write=30.0, pool=30.0)


http_client = httpx.Client(
    timeout=timeout,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=True,   # safe even if you think no proxy
)

aoai_client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key = os.getenv("AZURE_OPENAI_KEY") ,
    api_version="2024-02-01",
    http_client=http_client,
    timeout=30.0,
    max_retries=1
)


def call_model(prompt):
    try:
        return aoai_client.chat.completions.create(
            model= os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                response_format={"type": "json_object"},  # 👈 Force valid JSON
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. Always respond strictly in JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1200,
                temperature=0.2,
                top_p = 1,
                frequency_penalty = 0,
                presence_penalty = 0,
        )
    except:
        print(f"132 {traceback.print_exc()}")
        return {}

text ="""
CORROSION
MATTERS
Tax Invoice
Place Of Supplier:
GSTIN No:36AGBPK7018H1ZJ
CORROSION MATTERS
7-1-28/4/4, Swathi Plaza,
Shyam Karan Road, Ameerpet
Hyderabad, Telangana, India -500016
Tele No: 040 2374 2567
Fax No: 040 2374 0544
Invoice No
DSV20252613
Invoice Date
08-08-2025
GSTIN
36AGBPK7018H1ZJ
GSTIN State Code
36
Work Order No & Date
TNCH/P01/1800298/33000906
Dated: 20/04/2024
Details of Buyer (Billed to)
Torrent Gas Chennai Private Limited
5th Floor, No 148 Ward no 147 zone 8
Acropolis Building, Dr Radhakrishnan Street ,
Mylapore, Chennai 600004
Tamil Nadu
GST No: 33AAHCT5406D1ZP
Details of Consignee(Shipped To)
Torrent Gas Chennai Private Limited
5th Floor, No 148 Ward no 147 zone 8
Acropolis Building, Dr Radhakrishnan Street ,
Mylapore, Chennai 600004
Tamil Nadu
GST No: 33AAHCT5406D1ZP
Sr No
Item Code
Description
SAC Code
UOM
Quantit
У
Unit Price
INR
Total Amount
10-10
1700284
MONITORING & CONTROL_M&M CP
998338
KM
40
400.00
16,000.00
10-20
1700285
PM_TRU_M&M CP
998338
EA
1
2,500.00
2,500.00
10-30
1700286
PM_ANODE GDN BED_M&M CP
998338
EA
I
2,500.00
2,500.00
Total
21,000.00
GST Tax Rate In IGST @ 18%
3,780.00
Grand Total
24,780.00
(Rupees: Twenty Four Thousand Seven Hundred And Eighty Only)
Please Make Payment to:CORROSION MATTERS
Bank Account No
008010200051581
Name of the Bank
Axis Bank Ltd
Address of the Bank
6-3-879/B First Floor,G Pulla Reddy building, Begumpet, Hyderabad 500 016
MICR Code
500211002
IFSC Code
UTIB0000008
PAN No:
AGBPK7018H
UDYAM Reg No.
UDYAM-TS-02-0016298
KB
Digitally signed by KB SWAROOP
For Corrosion Matters
DN: CHIN, O CORROSION
Received Date
23/1/26
PO No.
:
GRN /SE No.
:
6-119874
IV Posting No.
:
101278
DCC Control No .:
SWAR
OOP
MATTERS, OU=ADMIN.
2 5.4.20=c2883d43da3791361dc
8911bba5c51a91032793085edc6
6c34d3f2cbBa9eec6,
postalCode=500016,
st=Telangana,
serialNumber=054a1ade26a24e6
eeb4-9744e8042407186720bac3
2bd61bc2605d680ed1319e,
cn=K B SWAROOP
Date: 2025.08.09 17:08:42 +05'30'
Authorised Signatory
IAF
"""
propmt ="""
You are an expert “PO Number Extractor” from unstructured documents (emails, invoices, PDFs converted to text, OCR, etc.). Your job is to extract ALL possible Purchase Order / Work Order / Reference No / Branch Sole ID / Service Order numbers from the given text.
 
====================
OUTPUT REQUIREMENT

Return ONLY a valid JSON object with EXACTLY this schema:

{"PoNo":[]}
 
- The value must be a list of strings.
- If no PO number can be confidently extracted, return:
{"PoNo":[]}
- Do NOT return any other keys, text, explanation, markdown, or extra whitespace outside the JSON.
 
====================

PO NUMBER DEFINITION
A PO number candidate may:
- Be purely numeric (e.g., "33001286", "96", "56")
- OR contain prefixes / division codes / identifiers
- May include separators like "/", "-", spaces

Examples of valid PO numbers:
"GJC1/P01/1800618/33001286"
"KJDH/P01/1865298/96000098"
"33001286"
"96"
"566"
"63364"

A PO number is typically a single “identifier-like” token, not a paragraph. 
====================
NORMALIZATION RULES

1) Treat these HTML entities as equivalent ONLY for label matching:
"&", "&amp;", "&amp;amp;" → treat all as "&"
2) Matching is case-insensitive.
3) Ignore extra spaces and punctuation differences in labels
   (e.g., "PO No", "PO No.", "P.O No" are equivalent)
4) The extracted PO value must be returned exactly as it appears in the text
   (trim surrounding spaces and punctuation only).
 
====================
LABEL HINTS (NON-PRIORITY)

These labels may indicate a PO number nearby, but NONE have priority over others:
- Buyer's Order No
- Buyers Order No
- Reference No
- Branch Sole ID
- Contract / PO Ref
- Contract Reference
- Work Order No
- WO No / W.O No
- Service Order No
- Dispatch Doc No
- Purchase Order No
- Customer PO No
- Order Ref
- PO No / P.O. No / PONO
(Labels are optional hints, not mandatory for extraction.)
 
====================
EXTRACTION STRATEGY

Step A — Global PO Discovery:
Scan the ENTIRE text and extract ALL identifier-like tokens that match the PO NUMBER DEFINITION:
- Tokens containing at least one digit
- Allowed characters: A–Z, a–z, 0–9, "/", "-", space
- Tokens may appear:
  - After labels (e.g., "PO No: 33001286", "WO No - TNCH/P01/...")
  - On the same line or the immediately next line
  - Anywhere in the document without labels
Prefer tokens that appear:
- Near keywords like:
  "PO", "Purchase Order", "Order", "Work Order", "WO",
  "Contract", "Service Order", "Reference"
====================

Step B — Candidate Validation & Cleaning:
For each extracted raw candidate:
- Trim spaces
- Remove surrounding quotes
- Remove trailing commas, periods, semicolons, brackets
- If multiple tokens are present together, split and keep valid PO-like tokens

A valid PO candidate MUST:
- Contain at least one digit
- Use only allowed characters: letters, digits, "/", "-", space
Reject obvious non-PO items such as:
- Dates (see DATE REJECTION RULE below)
- Phone numbers (10+ digit continuous numbers or country-code patterns)
- Email IDs or URLs
- Tax IDs (GSTIN, PAN, etc.) when clearly indicated
If unsure, prefer keeping the identifier-like token.
 
====================
Step C — Deduplication:
- Remove duplicate PO numbers (case-insensitive comparison)
- Preserve original formatting as it appears in the text

====================
Step D — Final Output:
- Return ALL valid, unique PO numbers as a list
- Order of the list should follow first appearance in the text

If no valid candidates exist:
{"PoNo":[]}
 
====================
DATE REJECTION RULE
Reject any candidate matching date-like formats, including:
- DD/MM/YY, DD/MM/YYYY
- DD-MM-YY, DD-MM-YYYY
- DD.MM.YYYY
- DTD: DD.MM.YYYY
- D-MMM-YY, DD-MMM-YY, D-MMM-YYYY (e.g., 1-Jan-26, 19-Jan-2026)
- YYYY-MM-DD, YYYY.MM.DD
 
====================
INPUT TEXT

"""

result = call_model(propmt + '\n' + text)

print(result)