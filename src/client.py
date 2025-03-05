#set openai api
from openai import OpenAI

global CLIENT
global MODEL_NAME
API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME =  "gpt-4o-mini"#"gpt-3.5-turbo-0125"
CLIENT = OpenAI(api_key=API_KEY)