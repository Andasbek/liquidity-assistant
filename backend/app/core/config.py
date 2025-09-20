import os
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения (.env в backend/ или корне проекта)
load_dotenv(find_dotenv())

# =========================
# LLM provider
# =========================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()     # "ollama" | "openai"
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# =========================
# Database
# =========================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://liquidity:liquidity@db:5432/liquidity"
)

# =========================
# Forecast / KPI
# =========================
DEFAULT_HORIZON_DAYS = int(os.getenv("DEFAULT_HORIZON_DAYS", "35"))  # T+35
REPORT_TIMEOUT_S = int(os.getenv("REPORT_TIMEOUT_S", "10"))          # отчет ≤10с
SCENARIO_TIMEOUT_S = int(os.getenv("SCENARIO_TIMEOUT_S", "5"))      # сценарий ≤5с
ALERT_WINDOW_DAYS = int(os.getenv("ALERT_WINDOW_DAYS", "14"))       # алерты на 14д

KPI_MAPE_TARGET = float(os.getenv("KPI_MAPE_TARGET", "12"))         # MAPE ≤12%
KPI_PRECISION_GAP_TARGET = float(os.getenv("KPI_PRECISION_GAP_TARGET", "0.8"))  # Precision ≥0.8

# =========================
# FX settings
# =========================
FX_PAIRS = [pair.strip() for pair in os.getenv("FX_PAIRS", "").split(",") if pair.strip()]
FX_SOURCE = os.getenv("FX_SOURCE", "csv")
FX_FFILL = os.getenv("FX_FFILL", "true").lower() == "true"

# =========================
# Scheduler
# =========================
SYNC_EVERY_MIN = int(os.getenv("SYNC_EVERY_MIN", "0"))  # 0 = выключено

# =========================
# Security / RBAC
# =========================
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_in_prod")
JWT_ISSUER = os.getenv("JWT_ISSUER", "liquidity-assistant")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "liquidity-users")
DEFAULT_ROLE = os.getenv("DEFAULT_ROLE", "Analyst")

# =========================
# Logging
# =========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

# =========================
# Misc
# =========================
TIMEZONE = os.getenv("TIMEZONE", "Asia/Almaty")
BASE_CURRENCY = os.getenv("BASE_CURRENCY", "KZT")
