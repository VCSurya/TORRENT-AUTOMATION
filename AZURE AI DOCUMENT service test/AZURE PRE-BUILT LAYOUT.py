from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

# 🔹 Replace with your Azure details
endpoint = os.getenv("AZURE_ENDPOINT")
key = os.getenv("AZURE_API_KEY")

# Initialize client
client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Path to your PDF
pdf_path = r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\PDFs\einv1 - 2025-09-10T173713.406 (1).pdf"

with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",   # "prebuilt-layout" extracts tables + text
        body=f,   # <--- use "body"
        content_type="application/pdf"
    )

result = poller.result()

# 🔹 Save tables to CSV
table_count = 0
for table_idx, table in enumerate(result.tables):
    # Find max rows and cols for table
    max_row = max(cell.row_index for cell in table.cells) + 1
    max_col = max(cell.column_index for cell in table.cells) + 1

    # Create empty 2D array
    data = [["" for _ in range(max_col)] for _ in range(max_row)]

    # Fill with table content
    for cell in table.cells:
        data[cell.row_index][cell.column_index] = cell.content

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Save as CSV
    table_count += 1
    csv_filename = f"table_{table_count}.csv"
    df.to_csv(csv_filename, index=False, header=False, encoding="utf-8-sig")
    print(f"✅ Saved {csv_filename}")
