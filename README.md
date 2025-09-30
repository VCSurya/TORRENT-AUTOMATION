# TORRENT-AUTOMATION

PDF Processing & SAP Integration API Documentation

This project is a robust system to process PDF invoices, extract relevant data using Azure Document Intelligence, format it with OpenAI LLM, and finally send both structured JSON data and PDF files to SAP OData API. It is built using Flask for API endpoints and a modular backend structure for processing and automation.

1. Flask API (`flask_api.py`)

This is the main API layer that exposes endpoints for uploading PDFs, viewing logs, editing prompts, and more. All endpoints interact with the core processing functions defined in `main.py`.

Endpoints:

* POST /upload_pdf
  Purpose: Accepts PDF files for processing.
  Input: JSON containing pdf_name and pdf_base64.
  Processing: Saves PDF temporarily, calls main.py methods, deletes PDF after processing.
  Output: Returns processed JSON with status and result.

* GET /help
  Purpose: Renders the help interface.
  Features: Displays latest logs, Azure extracted text and coordinates, OpenAI responses, prompt templates, final output JSON.

* POST /edit-prompt
  Purpose: Allows users to edit the OpenAI prompt template from frontend.
  Processing: Updates prompt.txt for subsequent PDF processing.

2. Core Processing (`main.py`)

Handles all PDF processing logic, including text extraction, data formatting, and SAP integration.

Key Functions:

* process_pdf(pdf_file): Processes a single PDF file.
* azure_extract_text(pdf_file): Sends PDF to Azure Document Intelligence and returns text with coordinates.
* format_with_llm(extracted_text): Uses OpenAI LLM to convert text into structured JSON.
* final_json(llm_json): Converts LLM output into final JSON for SAP integration.
* send_data_to_sap(json_data): Sends structured JSON to SAP OData API.
* send_pdf_to_sap(pdf_base64): Sends original PDF to SAP A11 storage.

3. Directory Structure:
   /latest: Stores data from latest processed PDF.
   /template: Contains help.html template.
   /upload_pdf: Temporary storage for uploaded PDFs.
   log_messages.json: Custom log file with status codes.
   pan.txt: Stores PAN numbers for GST identification.
   prompt.txt: Default OpenAI prompt template.
   sap.json: Default SAP API JSON template.

4. Features and Highlights:

* Seamless PDF Processing
* Azure Integration
* OpenAI LLM
* SAP API Integration
* Custom Logs & Templates
* Frontend Help Interface

5. Workflow Overview:
6. User uploads PDF via /upload_pdf.
7. PDF saved temporarily.
8. process_pdf() orchestrates extraction, formatting, JSON finalization, and SAP sending.
9. Temporary PDF deleted.
10. Logs, extracted text, and outputs saved in /latest.
11. Users view results in /help and modify prompt via /edit-prompt.

This setup ensures robust, end-to-end automation for processing PDFs, extracting structured data, and integrating seamlessly with SAP.
