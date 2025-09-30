import json
import ast 

# text format data
with open("latest/latest_pdf_azure_text.txt",'r',encoding='utf-8') as file:
        TEXT = file.read()

# json format data
with open("latest/latest_pdf_azure_text_cordinates.json", 'r', encoding='utf-8') as file:
    WORD_CORDINATES = json.load(file)

# json format data
with open("latest/latest_pdf_output.json", 'r', encoding='utf-8') as file:
    FINAL_JSON = json.load(file)

# text format data
with open("latest/latest_pdf_logs.txt", 'r', encoding='utf-8') as file:
    content = file.read()
    LOGS = ast.literal_eval(content)  # Safely parse string to list

# text format data
with open("latest/latest_pdf_open_ai_respons.txt", 'r', encoding='utf-8') as file:
    OPEN_AI_RESPONS = file.read()

