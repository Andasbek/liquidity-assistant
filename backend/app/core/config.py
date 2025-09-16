import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # подхватит backend/.env или корневой .env

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()          # "ollama" | "openai"
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1")               # имя модели
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8001/v1")  # ваш OpenAI-совместимый хост
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")             # токен, если требуется

# Таймауты / параметры
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
