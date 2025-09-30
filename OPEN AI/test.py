from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

text = None

with open(r"out.txt",'r',encoding='utf-8') as f:
    text = str(f.read())

# Environment variables
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")     # e.g. https://my-resource.openai.azure.com/
key = os.getenv("AZURE_OPENAI_KEY")               # API key from Azure portal
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") # Deployment name in Azure (e.g. gpt-4.1-mini)

# Create Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=key,
    api_version="2024-02-01"
)

prompt = f"""
You are an information extraction system. I will provide you with raw text extracted from an invoice or bill PDF. 

Your task:
- Extract only the requested fields according to the given JSON schema.
- Always return strictly valid JSON output, no explanations or extra text.

JSON Schema (follow exactly):
{{
    "Gst" : [],             // list of GST numbers
    "InvoiceNo" : "",       // invoice or bill number
    "InvoiceDate" : "",     // date in YYYY-MM-DD format
    "InvoiceAmount" : "",   // total invoice amount
    "IrnNo" : "",           // 64-character IRN number
    "PoNo" : "",            // Purchase Order number (also written as PO, Purchase Order, PO No.)
    "PAN Numbers" : [],     // list of PAN numbers
    "Email Id" : "",        // email id
    "SesGrn" : []           // list of SES / GRN / SCROLL numbers
}}

STRICT RULES:
1. Do not hallucinate. If a field is not found, return "" for strings and [] for lists.
2. "InvoiceDate" must always be normalized into YYYY-MM-DD format. If parsing fails, return "".
3. "InvoiceAmount" should contain only numbers (no currency symbols, commas are allowed).
4. If multiple GST, PAN, or SES/GRN/SCROLL numbers exist, include all of them inside their respective arrays.
5. "IrnNo" must always be exactly 64 hexadecimal characters (0-9, a-f). 
   - If the IRN is broken into two or more lines, join them together. 
   - Only accept a string of exactly 64 characters; otherwise return "".
6. "PoNo" specifically means Purchase Order Number. 
   - It may be written as "PO", "PO No.", or "Purchase Order No." 
   - Extract only that value if present.
7. Do not change field names, add new fields, or remove fields.
8. Final output must be valid JSON only.

Here is the PDF text:
{text}
"""


# Call GPT-4.1-mini with forced JSON output
response = client.chat.completions.create(
    model=deployment,
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
    max_tokens=1500,
    temperature=0
)


print(response)

print(">>> json")
# Print JSON output
print(response.choices[0].message.content)
