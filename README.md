# Liquidity Assistant — Финансовый AI-ассистент для управления ликвидностью

MVP-система для прогнозирования ежедневных денежных потоков, моделирования сценариев («what-if») и формирования коротких управленческих рекомендаций (LLM) для CFO/казначейства.

## Содержание
- [Функциональность](#функциональность)
- [Архитектура](#архитектура)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
  - [Локально](#локально)
  - [Docker Compose](#docker-compose)
- [Конфигурация (.env)](#конфигурация-env)
- [Схемы входных данных (CSV)](#схемы-входных-данных-csv)
- [API (FastAPI)](#api-fastapi)
- [Фронтенд (Streamlit)](#фронтенд-streamlit)
- [Интеграция LLM](#интеграция-llm)
- [Тестовые/Dev-эндпоинты](#тестовыedev-эндпоинты)
- [Траблшутинг](#траблшутинг)
- [Роадмап](#роадмап)
- [Лицензия](#лицензия)

---

## Функциональность
- Загрузка банковских операций, платёжного календаря и курсов FX (CSV).
- ETL → витрина `daily_cash` (нетто-поток по дням и кумулятивный баланс).
- Прогноз ликвидности (ARIMA/наивный fallback) + базовые метрики (sMAPE).
- Сценарии: FX-шок и задержки inflow/outflow.
- Advisor: список действий по правилам + LLM-сводка для CFO.
- Экспорт краткого брифа (Markdown).

## Архитектура
- **Backend**: FastAPI (ETL → Forecast → Scenario → Advisor).
- **Frontend**: Streamlit (дашборд + загрузка + графики + бриф).
- **LLM**: локальный Ollama или OpenAI-совместимый endpoint (vLLM и др.).
- Хранилище артефактов: `data/processed/` (Parquet при наличии `pyarrow`, иначе CSV-fallback).

## Структура репозитория
```

liquidity-assistant/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI, регистрация роутов
│  │  ├─ routers/
│  │  │  ├─ upload.py             # /api/upload (CSV → витрина)
│  │  │  ├─ forecast.py           # /api/forecast
│  │  │  ├─ scenario.py           # /api/scenario
│  │  │  ├─ advice.py             # /api/advice
│  │  │  ├─ llm\_test.py           # /api/llm/test (диагностика LLM)
│  │  │  └─ dev\_seed.py           # /api/dev/seed (сидер синтетики)
│  │  ├─ services/
│  │  │  ├─ etl.py                # normalize() + build\_daily\_cashframe()
│  │  │  ├─ forecast.py           # pmdarima и fallback
│  │  │  ├─ scenarios.py          # FX-шок, задержки
│  │  │  ├─ advisor.py            # правила + вызов LLM
│  │  │  └─ llm.py                # клиент Ollama/OpenAI-совместимый
│  │  ├─ core/config.py           # загрузка .env, LLM конфиг
│  │  └─ utils/io.py              # save\_df/load\_df с parquet→csv fallback
│  ├─ requirements.txt, Dockerfile
├─ frontend/
│  ├─ app.py, pages/\*, requirements.txt, Dockerfile
├─ infra/
│  └─ docker-compose.yml
├─ data/processed/                # артефакты ETL (parquet/csv)
└─ .env.example

````

---

## Быстрый старт

### Локально
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# (рекомендуется для Parquet)
pip install "pyarrow>=15,<18"
uvicorn app.main:app --reload

# Frontend
cd ../frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Запуск (API_URL можно задать в сайдбаре)
python -m streamlit run app.py
````

Открой: `http://127.0.0.1:8501`

### Docker Compose

```bash
cd infra
docker compose up --build
```

* Backend: `http://localhost:8000` (Swagger: `/docs`)
* Frontend: `http://localhost:8501`

---

## Конфигурация (.env)

Создайте `backend/.env` (или прокиньте переменные через Compose):

```env
# LLM
LLM_PROVIDER=ollama             # ollama | openai | (пусто = без LLM)
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://127.0.0.1:11434

# OpenAI-совместимый вариант:
# LLM_PROVIDER=openai
# OPENAI_BASE_URL=http://your-vllm-host:8001/v1
# OPENAI_API_KEY=your_token

# Дополнительно:
# LLM_TIMEOUT=60
```

Frontend читает `API_URL` из переменной окружения и/или поля в сайдбаре (по умолчанию `http://127.0.0.1:8000/api`).

---

## Схемы входных данных (CSV)

**bank\_statements.csv**

```
date,account,currency,amount
2025-08-01,MAIN,KZT,200000
2025-08-01,MAIN,USD,-1000
```

> `amount`: inflow (+), outflow (−)

**payment\_calendar.csv**

```
date,type,currency,amount,memo
2025-08-03,inflow,KZT,500000,Client invoice
2025-08-07,outflow,KZT,650000,Payroll
```

> `type`: `inflow|outflow` → знак применяется при normalize()

**fx\_rates.csv**

```
date,USD/KZT,EUR/KZT
2025-08-01,500,540
2025-08-02,501,539.5
```

> Пары вида `XXX/KZT`. ETL делает ffill/bfill по каждой валюте.

Артефакт ETL: **daily\_cash.(parquet|csv)** → `date, net_cash, cash_balance`.

---

## API (FastAPI)

Базовый префикс: `/api`
Swagger: `http://localhost:8000/docs`

### `POST /upload`

Загрузка трёх CSV → нормализация/сохранение → сборка витрины.

```bash
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "files=@bank_statements.csv" \
  -F "files=@payment_calendar.csv" \
  -F "files=@fx_rates.csv"
```

Ответ:

```json
{"loaded":{"bank_statements.csv":123,"payment_calendar.csv":45,"fx_rates.csv":60,"daily_cash.parquet":61}}
```

### `POST /forecast`

```json
{ "horizon_days": 14 }
```

Ответ:

```json
{
  "forecast": [{"date":"2025-09-20","net_cash":10000.0,"cash_balance":123456.0}, ...],
  "metrics": {"smape": 12.34}
}
```

### `POST /scenario`

```json
{"horizon_days":14,"fx_shock":0.1,"delay_top_inflow_days":7,"delay_top_outflow_days":0}
```

Ответ:

```json
{"forecast_scenario":[...],"min_cash":-250000.0,"metrics":{"smape":12.34}}
```

### `POST /advice`

```json
{"baseline": {...}, "scenario": {...}}
```

Ответ:

```json
{"advice_text":"...", "actions":[{"title":"Открыть ККЛ","amount":275000.0,"rationale":"..."}]}
```

### Диагностика

* `GET /health` → `{"status":"ok"}`
* `GET /llm/test` → провайдер/модель/пробный ответ LLM

---

## Фронтенд (Streamlit)

* Сайдбар: `API URL`, `Горизонт`, загрузка 3 CSV, кнопка «Загрузить».
* Главная: «Сделать прогноз» → график; «Сценарии» → FX-шок/задержки; «Совет» → текст LLM + список действий; «Экспорт брифа» (Markdown).
* Индикаторы статуса (опционально): пинг `/health` и `/llm/test`.

Запуск:

```bash
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

---

## Интеграция LLM

### Ollama (локально)

```bash
brew install --cask ollama
brew services start ollama
ollama pull llama3.1
curl http://127.0.0.1:11434/api/tags
```

`.env` (backend):

```
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Проверка: `curl http://127.0.0.1:8000/api/llm/test`

### OpenAI-совместимый endpoint

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://your-vllm-host:8001/v1
OPENAI_API_KEY=your_token
LLM_MODEL=meta-llama/Meta-Llama-3-8B-Instruct   # пример
```

---

## Тестовые/Dev-эндпоинты

* `POST /api/dev/seed` — генерирует синтетические CSV/Parquet и строит витрину (удобно для демо без файлов).
* `GET /api/llm/test` — проверка соединения с LLM.

> Dev-роуты не публикуйте наружу в продакшене.

---

## Траблшутинг

* **400 /api/upload**
  Проверьте: имена файлов (`bank_statements.csv`, `payment_calendar.csv`, `fx_rates.csv`), соответствие схем, кодировку (UTF-8). Сервер вернёт `detail` с подсказкой.
* **`python-multipart`**
  Установите `python-multipart`.
* **Parquet engine отсутствует**
  Установите `pyarrow` или используйте CSV-fallback в `utils/io.py`.
* **LLM: `Connection refused`**
  Запустите Ollama (`brew services start ollama`) или укажите корректный `OPENAI_BASE_URL`. Проверьте `/api/llm/test`.
* **Streamlit: `No module named 'dotenv'`**
  Установите `python-dotenv` именно в то окружение, где запускаете `streamlit`.

---

## Роадмап

* Модели прогноза: Prophet/NeuralProphet/LightGBM; календарные фичи (праздники/выходные).
* БД: Postgres + миграции (Alembic).
* Аутентификация/роли; разграничение данных.
* Отчёты PDF (WeasyPrint/ReportLab) и e-mail рассылка.
* Мониторинг/алерты (Prometheus/Grafana, Sentry).

---

## Лицензия

MIT
