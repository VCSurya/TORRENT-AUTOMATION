import os
import ssl
import main 
import shutil
import base64
import hashlib
import asyncio
import importlib
import traceback
import json, ast
import azure_emails_read
import configparser
import multiprocessing
from flask_cors import  CORS
from dotenv import load_dotenv
from datetime import datetime,timezone,timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify,render_template,send_file,redirect,url_for
from flask_login import LoginManager,login_user,login_required,logout_user,UserMixin,current_user
from PIL import Image

app = Flask(__name__)

CORS(app)

app.secret_key = "TGPL_SURYA"

config = configparser.ConfigParser()
config.read("login.ini")

login_manger = LoginManager(app)
login_manger.login_view = "home"

process_ref = shared_data = manager =None

scheduler= BackgroundScheduler()
scheduler.start()

# Directory where PDFs will be stored for temperery
PDF_SAVE_DIR = "uploaded_pdfs"
ENV_FILE = ".env"

#--------------------- ALL FUNCTIONS DEFINE HERE ---------------------

def hash_password(password: str) -> str:
    # Encode the password and compute SHA-256 hash
    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hashed

def save_env(env_data):
    """Save dictionary back to .env file"""

    with open(ENV_FILE, "w") as f:
        
        for k, v in env_data.items():
            f.write(f'{k}={v}\n')
            
def update_env(key, value):
    """Add or update an environment variable"""
    env_data = read_env()
    env_data[key] = value
    save_env(env_data)

def load_env():
    """Load environment variables from .env"""
    if not os.path.exists(ENV_FILE):
        open(ENV_FILE, 'w').close()  # create empty if not exists
    load_dotenv(ENV_FILE)

def read_env():
    """Return all env vars as a dictionary"""
    load_env()
    env_data = {}
    with open(ENV_FILE, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                env_data[key.replace(" ","")] = value.replace(" ","")
    return env_data

def convert_to_graph_utc(dt_str: str) -> str:
    """
    Convert user-visible mailbox time (no seconds, local time UTC+05:30)
    into the same UTC format returned by Azure Graph API.
    """
    # 1. Add seconds if missing
    # Example: 2025-11-17T11:38 -> 2025-11-17T11:38:00
    if len(dt_str) == 16:
        dt_str += ":00"
 
    # 2. Parse local datetime
    dt_local = datetime.fromisoformat(dt_str)
 
    # 3. Assign local timezone (UTC+05:30)
    local_tz = timezone(timedelta(hours=5, minutes=30))
    dt_local = dt_local.replace(tzinfo=local_tz)
 
    # 4. Convert to UTC
    dt_utc = dt_local.astimezone(timezone.utc)
 
    # 5. Return in Graph API style
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S+00:00")

async def maintain_logs(filename):

    try:
        existing_logs = []
        if os.path.exists(f'latest/{filename}'):  # Check if the file exists and is not empty
            with open(f'latest/{filename}', "r") as f:
                try:
                    existing_logs = json.load(f)  # Load the existing logs
                except json.JSONDecodeError:
                    existing_logs = []  # If the file is empty or corrupted, treat it as an empty list
        else:
            existing_logs = []  # If the file does not exist or is empty, start with an empty list

        if len(existing_logs) > 50:
            
            new_logs = existing_logs[-30:]

            with open(f'latest/{filename}', "w") as file:
                    json.dump(new_logs, file, indent=4)

    except Exception as e:
        print(str(e))

def update_logs():

    global shared_data

    safe_data = {}

    # ---- copy top-level shared_data safely ----
    for key, value in shared_data.items():
        safe_data[key] = value


    # ---- safely convert proceed_emails ----
    proceed_emails = []

    if 'proceed_emails' in shared_data:

        for _, email_data in shared_data['proceed_emails'].items():

            if isinstance(email_data, dict):
                clean_email = dict(email_data)  # deep copy per record
                clean_email.pop("id", None)     # remove id safely
                proceed_emails.append(clean_email)

    safe_data['proceed_emails'] = proceed_emails

    if len(safe_data.get('proceed_emails',[])) == 0:
        return    

    # ---- safely copy status ----
    safe_data["status"] = list(shared_data.get("status", []))

    
    if "last_visited_email_detailes" in safe_data:
        latest = {
            "id": safe_data['last_visited_email_detailes']['id'],
            "email_date_time": safe_data['last_visited_email_detailes']['email_date_time'],
        }
        safe_data['last_visited_email_detailes'] = latest
    
    else:
        safe_data['last_visited_email_detailes'] = {}
        

    # Append mode: keep previous logs if file exists
    if os.path.exists('latest/read_emails_logs.json'):  # Check if the file exists and is not empty
        with open('latest/read_emails_logs.json', "r") as f:
            try:
                existing_logs = json.load(f)  # Load the existing logs
            except json.JSONDecodeError:
                existing_logs = []  # If the file is empty or corrupted, treat it as an empty list
    else:
        existing_logs = []  # If the file does not exist or is empty, start with an empty list

    existing_logs.append(safe_data)

    with open("latest/read_emails_logs.json", "w") as f:
        json.dump(existing_logs, f, indent=4)
    
    asyncio.run(maintain_logs("read_emails_logs.json"))
        
def clear_dirs():
    try:
        temp_dir = os.path.join(os.getcwd(), 'temp')
        uploaded_pdfs_dir = os.path.join(os.getcwd(), 'uploaded_pdfs')

        # Remove files first if any
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        # Now remove the empty temp directory

        if os.path.exists(uploaded_pdfs_dir):
            for file in os.listdir(uploaded_pdfs_dir):
                file_path = os.path.join(uploaded_pdfs_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            shutil.rmtree(uploaded_pdfs_dir)  # Remove the empty uploaded_pdfs directory

    except Exception as e:
        print(f"An error occurred: {e}")

async def update_manual_logs(result):
        
        # Append mode: keep previous logs if file exists
        if os.path.exists('latest/upload_pdf_logs.json'):  # Check if the file exists and is not empty
            with open('latest/upload_pdf_logs.json', "r") as f:
                try:
                    existing_logs = json.load(f)  # Load the existing logs
                except json.JSONDecodeError:
                    existing_logs = []  # If the file is empty or corrupted, treat it as an empty list
        else:
            existing_logs = []  # If the file does not exist or is empty, start with an empty list

        if result['status']:
            
            existing_logs.append({
                    "status":result.get("status"),
                    "no":result.get("no"),
                    "PDF_FileName":result.get("PDF_FileName"),
                    "Date":datetime.strptime(result.get("json").get('CreatedOn'), "%Y%m%d").strftime("%d/%m/%Y"),
                    "Time":result.get("json").get('CreatedOnTime'),
            })

        else:
            result['Date'] = datetime.strptime(result.get("json").get('CreatedOn'), "%Y%m%d").strftime("%d/%m/%Y")
            result['Time'] = result.get("json").get('CreatedOnTime')
            existing_logs.append(result)

        with open("latest/upload_pdf_logs.json", "w") as f:
            json.dump(existing_logs, f, indent=4) 
        
        maintain_logs("read_emails_logs.json")



def update_json_file(file_path: str, data: dict) -> bool:
    
    try:
        
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

        return True
    
    except Exception as e:
        return False

def get_bot_status():
    
    with open('bot/bot_status.json' , "r") as file:
        data = json.load(file)

    return data

def load_schedule_config():
    try:
        with open("bot/scheduler.json", 'r') as f:
            return json.load(f)
    except Exception:
        return {"enable": False, "interval_minutes": 5}

# def run_async_target(shared_data):
#     importlib.reload(read_email)
#     asyncio.run(read_email.get_emails_and_download_attachments(shared_data))

def run_async_target(shared_data):
    try:
        importlib.reload(azure_emails_read)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Run async function
        loop.run_until_complete(azure_emails_read.process_filtered_emails(shared_data))
        loop.close()
        # Process finished successfully
        os._exit(0)
    except Exception as e:
        shared_data["status"].append(f"Fatal error in process: {e}")
        os._exit(1)  # Only set 1 if a real exception occurs

def start_process():

    """Start an async function in a separate process."""
    global process_ref,shared_data
    clear_dirs()

    if process_ref and process_ref.is_alive():
        # print("[+] Process already running.")
        return

    manager = multiprocessing.Manager()
    shared_data  = manager.dict()
    shared_data["proceed_emails"] = manager.dict()
    shared_data["status"] = manager.list(["1. Process initializing"])
    process_ref = multiprocessing.Process(target=run_async_target,args=(shared_data,))
    process_ref.start()
    shared_data["status"].append(f"2. Started process PID: {process_ref.pid}")

def stop_process():
    """Stop the running process cleanly."""
    
    try:
        global process_ref,shared_data
        clear_dirs()

        if process_ref and process_ref.is_alive():

            shared_data["status"].append(f"Terminating process PID: {process_ref.pid}...")

            # print(f"[Main] Terminating process PID: {process_ref.pid}...")
            
            process_ref.terminate()
            process_ref.join()
            shared_data["status"].append(f"Process terminated successfully.")
            
            update_logs()
            return {"status":True,"msg":"Process terminated successfully."}

            # print("[Main] Process terminated successfully.")
        else:
            # print("[Main] No process running.")
            return {"status":False,"error":"No process running."}

    except Exception as e:
        return {"status":False,"error":str(e)}

def scheduled_bot_run():
    status = get_bot_status()
    if not status["run"]:
        global process_ref,shared_data,manager

        # print('[Scheduler] Triggering bot run (bot was not running)')
        
        bot_data = {
            "run":True,
            "start_bot_date_time":f"{datetime.now()}"
        }

        update_json_file("bot/bot_status.json",bot_data)
        
        start_process()
        process_ref.join()
        
        if process_ref.exitcode == 0:
            shared_data["status"].append(f"-> Process completed normally")
            bot_data['Process completed normally'] = True
            
        else:
            shared_data["status"].append(f"-> Process not completed normally its terminate")
            bot_data['Process completed normally'] = False

        update_logs()

        bot_data['run'] = False
        bot_data['end_bot_date_time'] = f"{datetime.now()}"
        
        job = scheduler.get_job('bot_schedule')
        
        with open("bot/scheduler.json","r") as file:
            data = json.load(file)

        if job:
            # Return the next run time
            bot_data['Next run time'] = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            data["Next run time"] = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
    

        update_json_file("bot/bot_status.json",bot_data)

        with open("bot/scheduler.json","w") as file:
            json.dump(data, file, indent=2)

        return {'status':True,"msg":""}

    else:
        # print('[Scheduler] Skipped: Bot already running')
        # print(status)
        return {'status':False,"msg":"Bot already running"}
 
def update_scheduler():
    try:
        config = load_schedule_config()
        stop_process()
        scheduler.remove_all_jobs()

        if config.get('enable'):
            job = scheduler.add_job(scheduled_bot_run, 'interval', minutes=int(config.get('interval_minutes', 5)), id='bot_schedule', replace_existing=True)
            return {'status':True,"next_run_time":job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}
        return {'status':True}
    
    except Exception as e:
        return {'status':False,"error":str(e)}

def simple_recreate_bot():  

    global scheduler

    try:

        job_id='bot_schedule'
        job = scheduler.get_job(job_id)
        
        if not job:
            return {"status":False,"msg":"Job Not Found!"}

        next_run_dt = job.next_run_time or (datetime.now(scheduler.timezone) + job.trigger.interval)
        interval_td = job.trigger.interval

        scheduler.remove_job(job_id)
        scheduler.remove_all_jobs()

        job = scheduler.add_job(
            scheduled_bot_run,
            'interval',
            minutes=int(interval_td.total_seconds()//60),
            id=job_id,
            next_run_time=next_run_dt,
            replace_existing=True
        )

        data = load_schedule_config()
        
        d1 = {
            "run": False,
            "Next run time": str(job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'))
        }

        d2 = {
            "interval_minutes": int(interval_td.total_seconds()//60),
            "enable": True,
            "last_updated_scheduler": str(datetime.now()),
            "duration": str(data.get("duration","minutes")),
            "Next run time": str(job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'))
        }

        update_json_file("bot/bot_status.json",d1)
        update_json_file("bot/scheduler.json",d2)
    
        return {"status":True}
    
    except Exception as e:
        return {"status":False,"error":str(e)}

def default():
    global scheduler,shared_data
    shared_data = None
    scheduler.remove_all_jobs()
    clear_dirs()
    stop_process()

    d1 = {
            "run": False
        }

    d2 = {
        "interval_minutes": 1,
        "enable": False,
        "duration": "minutes",
        "last_updated_scheduler": str(datetime.now()),
    }

    update_json_file("bot/bot_status.json",d1)
    update_json_file("bot/scheduler.json",d2)

#--------------------- ALL ROUTES DEFINE HERE -----------------------

@app.route("/reset-bot",methods=["GET"])
@login_required
def reset_bot():

    try:
        global process_ref
        scheduler.remove_all_jobs()
        stop_process()
        
        scheduler_data = {
            "interval_minutes": 1,
            "enable": False,
            "duration": "minutes",
            "Next run time": ""
        }

        with open("bot/scheduler.json", "w") as file:
            json.dump(scheduler_data, file, indent=4)

        bot_status = {
            "run": False
        }

        with open("bot/bot_status.json", "w") as file:
            json.dump(bot_status, file, indent=4)

        with open("latest/read_emails_logs.json", "w") as file:
            json.dump([], file, indent=4)

        clear_dirs()

        import time
        time.sleep(3)
        return jsonify({"success":True,"msg":"Bot Reset Sucessfully."})

    except Exception as e:
        return jsonify({"success":False,"error":str(e)})
        
@app.route("/skip",methods=["GET"])
@login_required
def skip_bot():
    try:
        
        import time
        time.sleep(5)
        result = simple_recreate_bot()
        stop_process()
        
        if result['status']:
            return {"success":True,"msg":f"Bot Skip Successfully."}
        
        return {"success":False,"error":f"Somthing Went Wrong!"}
    
    except Exception as e:
        return {"success":False,"error":f"Error: {str(e)} Durring Bot Stop."}

# start the bot immediately
@app.route("/start",methods=["GET"])
@login_required
def start_bot():
    global scheduler
    try:
        
        data = load_schedule_config()

        if data.get('enable'):
            return {"success":False,"error":"Please First Disable the Scheduler!"}
            
        scheduler.remove_all_jobs()
        stop_process()

        if not data.get('enable'):
            job = scheduler.add_job(scheduled_bot_run, trigger="date", id='bot_schedule', replace_existing=True)
            return {'status':True,"next_run_time":job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}
        
        return {'status':True}
        
        # if not result['status']:
        #     return {"success":False,"error":result['msg']}
        # else:
        #     return {"success":True}

    except Exception as e:
        return {"success":False,"error":f"Error: {str(e)} Durring Bot Start."}


@app.route("/stop",methods=["GET"])
@login_required
def stop_bot():
    global scheduler
    try:
        
        scheduler.remove_all_jobs()
        stop_process()

        data = load_schedule_config()
        
        d1 = {
            "run": False,
        }

        d2 = {

            "enable": False,
            "last_updated_scheduler": str(datetime.now()),
            "duration": str(data.get("duration","minutes")),
            "interval_minutes": data.get("interval_minutes","1")
            
        }

        update_json_file("bot/bot_status.json",d1)
        update_json_file("bot/scheduler.json",d2)

        return {"success":True,"msg":"Bot Stoppped..."}

    except Exception as e:
        return {"success":False,"error":f"Error: {str(e)} Durring Bot Stop."}


@app.route("/update_scheduler",methods=["POST","GET"])
@login_required
def update_scheduler_method():
    
    """
    {
      inputValue: "1"
      isChecked: true
      selectedTime: "minutes"
    }
    """
    try:
        
        if request.method == 'POST':
        
            status = get_bot_status()
            
            if not status["run"]:
            
                data = request.get_json()
                scheduler_data = {}

                if data['isChecked'] and int(data['inputValue']) > 0:
                    
                    if data['selectedTime'] == "minutes":
                        scheduler_data = {
                            "interval_minutes":int(data['inputValue']),
                            "enable":True,
                            "duration":"minutes"
                        }

                    elif data['selectedTime'] == "hours":
                        scheduler_data = {
                            "interval_minutes":int(data['inputValue'])*60,
                            "enable":True,
                            "duration":"hours"

                        }
                    else:
                        return jsonify({"success":False,"error":"Enter Valid Input Try Again!"})

                else:
                    scheduler_data = {
                        "interval_minutes":1,
                        "enable":False,
                        "duration": "minutes"
                    }
                    
                
                scheduler_data["last_updated_scheduler"] = str(datetime.now())

                with open("bot/scheduler.json", "w") as file:
                    json.dump(scheduler_data, file, indent=4)

                res = update_scheduler()

                if res["status"]:

                    if res.get("next_run_time"):
                        scheduler_data["Next run time"] = res["next_run_time"]         
                        
                        bot_data = {
                            "run":False,
                            "Next run time": scheduler_data["Next run time"]
                        }
                        update_json_file("bot/bot_status.json",bot_data)

                        with open("bot/scheduler.json", "w") as file:
                            json.dump(scheduler_data, file, indent=4)

                    return jsonify({"success":True,"msg":"scheduler update successfully"})
                else:
                    return jsonify({"success":True,"msg":"error in updating scheduler try again"})
            else:
                return jsonify({"success":True,"msg":"Bot is running, error in updating scheduler first stop the bot!"})
        else:

            with open("bot/scheduler.json", 'r', encoding='utf-8') as file:
                bot_scheduler = json.load(file)

            if bot_scheduler['duration'] == 'hours':
                bot_scheduler['interval_minutes'] = int(bot_scheduler['interval_minutes']/60); 

            return jsonify({"success":True,"bot_scheduler":bot_scheduler})
            
    except Exception as e:
        return jsonify({"success":False,"error":f"505: {str(e)}"})

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        data = request.get_json()

        pdf_name = data.get("pdf_name", "")
        pdf_base64 = data.get("pdf_base64", "")
        Mode_Of_Entry = data.get("mode_of_entry", "Manual")
        Created_On = data.get("created_on", "20250206")
        Created_By = data.get("created_by", "DEVESH")

        
        if not pdf_name or not pdf_base64:
            return jsonify({"Error":0,"Error Msg": "Missing 'pdf_name' or 'pdf_base64'"}), 400

        # Ensure .pdf extension
        if pdf_name.lower().split(".")[-1] not in ["pdf","jpg","jpeg","png"]:
            return jsonify({'success':"", "error": "Upload Only pdf, jpg, jpeg and png File Format."}), 501
        
        # Decode base64 string
        pdf_bytes = base64.b64decode(pdf_base64)

        # Save file
        os.makedirs(PDF_SAVE_DIR, exist_ok=True)
        file_path = os.path.join(PDF_SAVE_DIR, pdf_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        if not pdf_name.lower().endswith(".pdf"):
            
            img = Image.open(file_path)
            img = img.convert("RGB")
            file_path = file_path+".pdf"
            img.save(file_path)

        email_data = {
                        "vandor_email":"",
                        "email_date_time":"",
                        "email_subject":"",
                        "SourceOfDoc":""
        }
        
        load_dotenv(override=True)
        importlib.reload(main)
        result = main.process_pdf(os.path.abspath(file_path),email_data,Mode_Of_Entry,Created_On,Created_By)
        asyncio.run(update_manual_logs(result))

        ### Note: if success is X means true and "" means false

        if result['status']:
            return jsonify({'success':'X','InwardRefNo':result.get('no'),'Status':result.get('json').get('Status',None)}), 200

        else:
            return jsonify({'success':"",'InwardRefNo':result.get('no') if result.get('no') else "",'error':f"{result['json']['ErrorNo']}:{result['json']['ErrorMsg']}" if result['json']['ErrorMsg'] or result['json']['ErrorNo'] else f"440 : Somthing Went Wrong At Server Side!",'Status':result.get('json').get('Status',None)}), 501
        
    except Exception as e:
        traceback.print_exc()  # print full error and line number to console
        return jsonify({'success':"", "error": f"{type(e).__name__}: {str(e)}"}), 500
    
    finally:

        dir_path = os.path.abspath(PDF_SAVE_DIR)

        if os.path.isdir(dir_path):
            for entry in os.listdir(dir_path):
                full_path = os.path.join(dir_path, entry)
                if os.path.isfile(full_path):
                    try:
                        os.remove(full_path)
                    except OSError as e:
                        print(f"Failed to remove file: {full_path} — {e}")


@app.route('/env-configuration',methods=['GET'])
@login_required
def env_get_configuration():
    try:
        data = read_env()

        # data['SCOPES'] = data['SCOPES'].replace("[","").replace("]","").replace("'",'').replace('"',"")
        data.pop('SCOPES')

        return render_template("configuration.html",data=data)

    except Exception as e:
        return jsonify(str(e))

@app.route('/update-configuration',methods=['POST'])
@login_required
def update_configuration():
    try:
        data = request.get_json()
        env_data = read_env()

        kay_name = data.get("kay_name")
        list_of_keys = list(env_data.keys())

        if kay_name in list_of_keys:
                
            update_env(kay_name,data.get("key_value"))
            
            return {"success":True,"msg":"Update Sucessfully!"}
        else:
            return {"success":False,"error":"Enter Valid Data!"}
    
    except Exception as e:
        return {"success":False,"error":f"{str(e)}"}

    finally:
        load_dotenv(override=True)

        
@app.route('/edit-prompt', methods=['POST'])
@login_required
def edit_prompt():
    try:
        data = request.get_json()
        if not data or ('prompt' not in data and 'num' not in data):
            return jsonify({'success':False,'error': 'Missing Data!'}), 400

        prompt_text = data['prompt']

        if data.get('num') == 0:
            with open('prompt_0.txt', 'w', encoding='utf-8') as f:
                f.write(prompt_text)

        elif data.get('num') == 1:
            with open('prompt_1.txt', 'w', encoding='utf-8') as f:
                f.write(prompt_text)
        else:
            return jsonify({'success':False,'error': 'Somthing Went Wrong!'}), 400

        return jsonify({'success':True,'msg': 'Prompt saved successfully'}), 200

    except Exception as e:
        return jsonify({'success':False,'error': str(e)}), 500

@app.route('/ram', methods=['GET'])
@login_required
def help():

    # Load data
    with open("latest/latest_pdf_azure_text.txt",'r',encoding='utf-8') as file:
        TEXT = file.read()

    with open("latest/latest_pdf_azure_text_cordinates.json", 'r', encoding='utf-8') as file:
        WORD_CORDINATES = json.dumps(json.load(file), indent=2)

    with open("latest/latest_pdf_output.json", 'r', encoding='utf-8') as file:
        FINAL_JSON = json.dumps(json.load(file), indent=2)

    with open("latest/latest_pdf_logs.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        LOGS = ast.literal_eval(content)  # Safely parse string to list
        LOGS = json.dumps(LOGS, indent=2)  # Format nicely for HTML

    with open("latest/latest_pdf_open_ai_respons.txt", 'r', encoding='utf-8') as file:
        OPEN_AI_RESPONS = file.read()

    with open("prompt_0.txt", 'r', encoding='utf-8') as file:
        PROMPT_TEMPLATE_0 = file.read()

    with open("prompt_1.txt", 'r', encoding='utf-8') as file:
        PROMPT_TEMPLATE_1 = file.read()
        
    with open("latest/read_emails_logs.json", 'r', encoding='utf-8') as file:
        READ_EMAILS_LOGS = json.dumps(json.load(file), indent=2)

    with open("latest/latest_sap_response.json", 'r', encoding='utf-8') as file:
        LATEST_SAP_RESPONSE = json.dumps(json.load(file), indent=2)
    
    with open("latest/latest_proceed_email.json", 'r', encoding='utf-8') as file:
        LAST_PROCEED_EMAIL = json.dumps(json.load(file), indent=2)

    return render_template('help.html',
                           TEXT=TEXT,
                           WORD_CORDINATES=WORD_CORDINATES,
                           FINAL_JSON=FINAL_JSON,
                           LOGS=LOGS,
                           OPEN_AI_RESPONS=OPEN_AI_RESPONS,
                           PROMPT_TEMPLATE_0=PROMPT_TEMPLATE_0,
                           PROMPT_TEMPLATE_1=PROMPT_TEMPLATE_1,
                           READ_EMAILS_LOGS=READ_EMAILS_LOGS,
                           LATEST_SAP_RESPONSE=LATEST_SAP_RESPONSE,
                           LAST_PROCEED_EMAIL=LAST_PROCEED_EMAIL)

@app.route("/logs", methods=['GET'])
@login_required
async def logs():

    try:

        logs = {}

        with open("bot/bot_status.json", 'r', encoding='utf-8') as file:
            bot_status = json.load(file)
        
        logs["bot_status"] = bot_status
        
        if not bot_status["run"]:

            with open('latest/read_emails_logs.json', "r") as f:
                try:
                    existing_logs = json.load(f)  # Load the existing logs
                    logs["data"] = existing_logs[-1]
                except:
                    logs["data"] = {}
            
            return {"success":True,"logs":logs}

        global shared_data
        if shared_data:
            safe_data  = dict(shared_data)
            safe_data['proceed_emails']  = dict(shared_data['proceed_emails'])
            safe_data["status"] = list(shared_data["status"])
            logs["data"] = safe_data
    
        return {"success":True,"logs":logs}

    except Exception as e:
        return {"success":False,"error":str(e)}

@app.route("/pdf")
@login_required
def serve_pdf():
    # Serve the PDF from disk. Set as inline so browsers render it in tab/viewer.
    return send_file(
        r"latest\latest.pdf",
        mimetype="application/pdf",
        as_attachment=False,  # inline display
        download_name="latest.pdf"  # name shown in viewer/tab
    )

@app.route("/user-logs")
@login_required
def all_logs():
    try:
        
        with open('latest/read_emails_logs.json','r',encoding='utf-8') as file:
            all_logs = json.load(file)
        return render_template('live_logs.html',LOGS=all_logs)
    
    except Exception as e:
        return{"error":str(e)}

@app.route("/manual-logs")
@login_required
def manual_logs():
    try:
        
        with open('latest/upload_pdf_logs.json','r',encoding='utf-8') as file:
            all_logs = json.load(file)
        return render_template('upload_logs.html',LOGS=all_logs)
    
    except Exception as e:
        return{"error":str(e)}


@app.route("/custom-logs",methods=['GET'])
@login_required
def custom_logs():
    
    try:

        with open('log_messages.json','r',encoding='utf-8') as file:
            logs = json.load(file)
        return logs
    
    except Exception as e:
        return{"error":str(e)}

@app.route("/latest-proceed-email",methods=['GET','POST'])
@login_required
def latest_proceed_email():

    try:

        if request.method == 'POST':

            data = request.get_json()
            
            updated_info = {
                "id":"HARE_KRISHNA_HARE_KRISHNA_KRISHNA_KRISHNA_HARE_HARE_HARE_RAM_HARE_RAM_RAM_RAM_HARE_HARE",
                "email_date_time":convert_to_graph_utc(data['new_process_date'])
            }    

            update_json_file("latest/latest_proceed_email.json",updated_info)

            return {"success":True,"msg":"Email Starting Point Updated!"}

        elif request.method == 'GET':
        
            with open("latest/latest_proceed_email.json","r") as file:
                data = json.load(file)

            return {"success":True,"date":data["email_date_time"]}

        else:
            
            return {"success":False,"msg":"Something Went Wrong at Server Side!"}


    except Exception as e:
        return {"success":False,"error":str(e)}

@app.route("/apple")
@login_required
def apple():
    load_dotenv()
    email = os.getenv("USER_ID")
    return render_template("index.html",email=email)

@app.route("/")
def home():
    if current_user.is_authenticated:
            return redirect(url_for("apple"))
    return render_template("login.html")

# Dummy User class
class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manger.user_loader
def load_user(user_id):
    return User(user_id)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password required"}), 400

    username = data["username"]
    password = data["password"]


    if username == config['LOGIN']['username'] and hash_password(config['LOGIN']['password']) == password:
        
        user = User(username)
        login_user(user)
        
        return jsonify({"result": "Sucessfully"}), 200
        
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.errorhandler(404)
def page_not_found(e):
    # If user is authenticated, redirect to index or dashboard
    if current_user.is_authenticated:
        return redirect(url_for("apple"))  # or your main page route
    else:
        return redirect(url_for("home"))  # login page route


if __name__ == '__main__':

    default()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    # Run Flask over HTTPS
    app.run(host='0.0.0.0', port=5000, ssl_context=context,debug=True)
    # app.run(host="0.0.0.0",port=5000,debug=True)
