# 🧾 **Automated PDF Processing & SAP Integration Bot**

A complete automation system for extracting PDFs from email, processing
them using Azure OCR + OpenAI LLM, formatting results into SAP-compliant
JSON, and submitting data to SAP OData services.\
Includes bot scheduling, logs viewer, control panel UI, authentication,
and extensive configuration tools.

## 🚀 **Features**

-   ✔ Automatic email reading & PDF extraction\
-   ✔ Azure OCR for text + coordinate extraction\
-   ✔ LLM for structured JSON generation\
-   ✔ SAP OData API integration (PDF + JSON posting)\
-   ✔ Scheduler-based bot automation\
-   ✔ Skip/Reset/Start/Stop bot operations\
-   ✔ Environment & prompt configuration via UI\
-   ✔ Detailed logs & latest processed PDF viewer\
-   ✔ Secure login system\
-   ✔ Fully modular and extensible

# 📂 **Project Structure**

    project/
    │
    ├── api.py                      # All backend APIs
    ├── main.py / .pyd              # Core processing engine (OCR, LLM, SAP)
    ├── read_email.py               # Email reading + attachment extraction
    │
    ├── latest/                     # Latest processing logs & outputs
    ├── upload_pdf/                 # Temporary PDFs folder
    ├── template/                   # Frontend HTML files
    │
    ├── bot/
    │   ├── bot_status.json         # Running/Stopped
    │   └── scheduler.json          # Interval, duration, enable flag
    │
    ├── log_messages.json           # Custom log codes
    ├── pan.txt                     # PAN backup list
    ├── sap.json                    # SAP OData JSON template
    ├── prompt_0.txt                # LLM prompt (non-QR)
    ├── prompt_1.txt                # LLM prompt (QR-based)
    ├── login.ini                   # Username/password store
    └── rough.py                    # Testing area

# 🔌 **API Endpoints**

## 📥 **PDF Processing**

### ▶ **POST `/upload_pdf`**

Uploads a PDF, runs processing, returns document number or error.

**Body:**

``` json
{
  "pdf_name": "",
  "pdf_base64": "",
  "mode_of_entry": "",
  "created_on": "",
  "created_by": ""
}
```

## 🤖 **Bot Control**

  Endpoint              Method     Description
  --------------------- ---------- -----------------------------------
  `/reset-bot`          GET        Reset all jobs & logs
  `/skip`               GET        Skip current bot run
  `/update_scheduler`   GET/POST   View or update scheduler config
  `/ram`                GET        Return latest OCR, LLM & SAP logs
  `/logs`               GET        Live logs stream
  `/custom-logs`        GET        Internal error logs

## ⚙️ **Environment & Prompt Management**

  Endpoint                  Method   Purpose
  ------------------------- -------- -----------------------------
  `/env-configuration`      GET      Returns `.env` values
  `/update-configuration`   POST     Update `.env`
  `/edit-prompt`            POST     Update LLM prompt templates

## 📧 **Email Information**

  Endpoint                  Method   Description
  ------------------------- -------- ------------------------------------
  `/latest-proceed-email`   GET      Get last processed email timestamp
  `/latest-proceed-email`   POST     Update timestamp

## 🖥️ **UI Components**

  Endpoint    Page
  ----------- -------------------
  `/apple`    Bot control panel
  `/`         Login page
  `/logout`   Logout
  `/pdf`      Latest PDF

# 🔧 **Core System Functions**

### 🧠 main.py (Processing Engine)

-   process_pdf()
-   azure_extract_text()
-   format_with_llm()
-   final_json()
-   send_data_to_sap()
-   send_pdf_to_sap()
-   process_pdfs()
-   pan_numbers()
-   pdf_to_image()
-   detect_qrs_from_image()
-   decode_qr_data()
-   extract_file_name()

### 📧 read_email.py

-   get_emails_and_download_attachments()
-   verify_signatures()
-   update_json_file()
-   get_folder_names()

### 🛠️ Utility Functions

Includes: - hash_password() - load_env(), read_env() - save_env(),
update_env() - update_logs() - update_json_file() -
simple_recreate_bot() - stop_process(), start_process() -
run_async_target() - clear_dirs() - get_bot_status() -
load_schedule_config() - scheduled_bot_run()

# 🔄 **System Workflow**

    Email Inbox
        ↓
    read_email.py → Save PDF
        ↓
    process_pdf()
        ↓
    1. PDF → Images
    2. QR Detection
    3. Azure OCR
    4. LLM Formatting
    5. SAP JSON Build
    6. SAP API Posting
        ↓
    Save Logs → /latest

# 🧪 Testing

Use `rough.py` for development experiments.

# 🔐 Authentication

Stored in `login.ini` (hashed passwords).

# 📝 Scheduler

Stored in `bot/scheduler.json`.

# 🛡️ Error Handling

Custom errors stored in `log_messages.json`.

------------------------------------------------------------------------
