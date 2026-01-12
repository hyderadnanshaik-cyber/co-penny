import os
from dotenv import load_dotenv

load_dotenv()

print("LLM_PROVIDER =", os.getenv("LLM_PROVIDER"))
print("GEMINI_API_KEY =", os.getenv("GEMINI_API_KEY"))
print("GEMINI_MODEL =", os.getenv("GEMINI_MODEL"))
