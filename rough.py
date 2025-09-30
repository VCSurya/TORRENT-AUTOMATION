LOGS = ['2', '3 boby.pdf', '4', '5', '6', '7', '8', '9', "10 \n\n{'Gst': ['09AAECS3538A1ZL', '09AAGC17889P1Z1'], 'InvoiceNo': 'BNUPAGR25000717', 'InvoiceDate': '2025-09-04', 'InvoiceAmount': '276446.76', 'IrnNo': 'cfece8cb5864879055da5e002878e47dde7dc28495208c44ec15041ce918c866', 'PoNo': 'UPAG/P01/1800096/33000926', 'PAN Numbers': ['AAECS3538A', 'AAGCT7889P'], 'Email Id': 'gstcomplianceteam@sisindia.com', 'SesGrn': []}", '11', "12 {'status': True}", '13', '14', '15', '16 0000000058', '17', '14', '15', '20']

import json

with open('log_messages.json', 'r') as file:
    logs = json.load(file)  # correctly loads JSON into a Python dictionary
    logs_steps = []

    for index,value in enumerate(LOGS):
        logs_steps.append(f"Step {index}: {value.replace(value.split()[0],logs[value.split()[0]])}")

    with open('latest/latest_pdf_logs.txt', 'w',encoding='utf-8') as file:
        file.write(str(logs_steps))
