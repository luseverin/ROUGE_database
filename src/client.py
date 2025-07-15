#set openai api
from openai import OpenAI
import instructor

global CLIENT
global MODEL_NAME
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"#"meta-llama/llama-4-scout-17b-16e-instruct"
## Examples of models with Groq :
MODEL_NAME_LIST = [
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mistral-saba-24b",
    "llama-3.1-8b-instant",
    "playai-tts",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "deepseek-r1-distill-llama-70b",
    "qwen-qwq-32b",
    "whisper-large-v3",
    "llama-guard-3-8b",
    "distil-whisper-large-v3-en",
    "llama-3.3-70b-versatile",
    "allam-2-7b",
    "gemma2-9b-it",
    "compound-beta-mini",
    "playai-tts-arabic",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-guard-4-12b",
    "compound-beta",
    "whisper-large-v3-turbo",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-prompt-guard-2-86m",
    "qwen-qwq-32b",
    "qwen/qwen3-32b"

]



if MODEL_NAME in ["gpt-4o-mini", "gpt-3.5-turbo-0125"] :
    API_KEY = os.getenv("GROQ_API_KEY")
    CLIENT = OpenAI(api_key=API_KEY)
else :
    API_KEY = os.getenv("GROQ_API_KEY")
    #"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" #Luca's
    #"os.getenv("GROQ_API_KEY")" Laura's
    CLIENT = OpenAI(
        api_key=API_KEY,
        base_url="https://api.groq.com/openai/v1"  # <-- Groq’s OpenAI-compatible endpoint
    )

# Enables `response_model`
CLIENT = instructor.patch(client=CLIENT)