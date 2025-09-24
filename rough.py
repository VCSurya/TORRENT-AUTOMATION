import os 
PROMPT = "ok"
text = "ram"
SCRTPT_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_path  = os.path.join(SCRTPT_DIR, 'prompt.txt')
with open(prompt_path, 'r') as file:
    PROMPT = file.read()

PROMPT = PROMPT + '\n' + text

print(PROMPT)
