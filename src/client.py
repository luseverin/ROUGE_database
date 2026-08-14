import requests
import pandas as pd
from openai import OpenAI
import instructor
import getpass
from dotenv import load_dotenv
import os 

##set groq api
# set up api key
API_KEY = os.getenv("GROQ_API_KEY")
# "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" #Luca's
# "os.getenv("GROQ_API_KEY")" Laura's

# set up client
CLIENT = OpenAI(api_key=API_KEY, base_url="https://api.groq.com/openai/v1")
# Enables `response_model`
CLIENT = instructor.patch(client=CLIENT)

# get model list
url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {API_KEY}"}
response = requests.get(url, headers=headers)
model_table = pd.DataFrame(response.json()["data"])
# Examples of models with Groq (from model table):
MODEL_NAME_LIST = [
    "playai-tts-arabic",
    "allam-2-7b",
    "qwen/qwen3-32b",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-prompt-guard-2-86m",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "whisper-large-v3-turbo",
    "moonshotai/kimi-k2-instruct-0905",
    "playai-tts",
    "meta-llama/llama-guard-4-12b",
    "moonshotai/kimi-k2-instruct",
    "groq/compound-mini",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "groq/compound",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-safeguard-20b",
    "whisper-large-v3",
]

# seelct model
MODEL_NAME = "llama-3.3-70b-versatile"#"meta-llama/llama-4-scout-17b-16e-instruct"

# retrieve max tokens
MAX_COMPLETION_TOKENS = model_table[model_table["id"] == MODEL_NAME][
    "max_completion_tokens"
].values[0]
CONTEXT_WINDOW = model_table[model_table["id"] == MODEL_NAME]["context_window"].values[
    0
]

## Nominatim
user = getpass.getuser()
if user == "lhasbini":
    NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT")
elif user == "lseverino":
    NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT")
else:
    raise ValueError(f"Cannot define nominatim user agent for unknown user: {user}")

## Montandon
# if user == "lhasbini":
MONTANDON_API_TOKEN = os.getenv("MONTANDON_API_TOKEN")
