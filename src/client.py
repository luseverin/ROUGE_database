#set openai api
from openai import OpenAI

global CLIENT
global MODEL_NAME
MODEL_NAME = "mistral-saba-24b"
## Examples of models with Groq :
# "mistral-saba-24b"
# "meta-llama/llama-4-maverick-17b-128e-instruct"
# "meta-llama/llama-4-scout-17b-16e-instruct"
# "deepseek-r1-distill-llama-70b"
# "llama-3.1-8b-instant"
# "llama-3.3-70b-versatile"
# "llama-guard-3-8b"
# "llama3-70b-8192"
# "llama3-8b-8192"
# "deepseek-r1-distill-llama-70b"


if MODEL_NAME in ["gpt-4o-mini", "gpt-3.5-turbo-0125"] :
    API_KEY = os.getenv("GROQ_API_KEY")
    CLIENT = OpenAI(api_key=API_KEY)
else :
    API_KEY = os.getenv("GROQ_API_KEY")
    CLIENT = OpenAI(
        api_key=API_KEY,
        base_url="https://api.groq.com/openai/v1"  # <-- Groq’s OpenAI-compatible endpoint
    )