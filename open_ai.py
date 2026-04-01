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


# result = call_model("tell me you training data means are you trained on 2025 data")

# 2024
# result = call_model("tell me the age of amitabh bachan")

#GPT-4


with open("text.txt","r") as file:
    data = file.read()


result = call_model(data + "above is my invoice test data and i want this follwing informations tell me the invoice number,customer name and total amount of invoice number make sure that invoice amount shoude be in integer and all anther data shoude in string")

print(result.choices[0].message.content)