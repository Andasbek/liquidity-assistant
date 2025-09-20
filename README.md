# Liquidity Assistant — Финансовый AI-ассистент для управления ликвидностью

MVP-система для **прогнозирования ежедневных денежных потоков**, моделирования **what-if сценариев** и формирования **кратких управленческих рекомендаций (LLM)** для CFO/казначейства. Есть экспорт **PDF-брифа**, страница **Backtest & сравнение моделей**, и опциональный workflow для автозапуска пайплайна.

## Содержание

* [Функциональность](#функциональность)
* [Архитектура](#архитектура)
* [Структура репозитория](#структура-репозитория)
* [Быстрый старт](#быстрый-старт)

  * [Локально](#локально)
  * [Docker Compose](#docker-compose)
* [Конфигурация (.env)](#конфигурация-env)
* [LLM-провайдеры (Ollama / vLLM / Groq)](#llm-провайдеры-ollama--vllm--groq)
* [Демо-данные и CSV-схемы](#демо-данные-и-csv-схемы)
* [API (FastAPI)](#api-fastapi)
* [Фронтенд (Streamlit)](#фронтенд-streamlit)
* [Отчёты PDF](#отчёты-pdf)
* [Backtest & сравнение моделей](#backtest--сравнение-моделей)
* [RBAC (роли)](#rbac-роли)
* [Инфра / Nginx / Healthchecks](#инфра--nginx--healthchecks)
* [Скрипты и тесты](#скрипты-и-тесты)
* [Shai Workflow (бонус)](#shai-workflow-бонус)
* [Траблшутинг](#траблшутинг)
* [Лицензия](#лицензия)

---

## Функциональность

* Загрузка банковских операций, платёжного календаря и курсов FX (CSV).
* ETL → витрина `daily_cash` (нетто-поток по дням и кумулятивный баланс).
* Прогноз ликвидности (ARIMA/наивный fallback) с базовыми метриками (sMAPE).
* Сценарии: FX-шок и задержки inflow/outflow.
* Advisor: правила ликвидности + LLM-бриф для CFO (деловой стиль, RU).
* Экспорт **PDF-брифа** (ReportLab; поддержка кириллицы).
* Страница **Backtest** (rolling window, MAPE/sMAPE, графики факт vs прогноз).
* Healthchecks, роль-бэйсд доступ (RBAC через заголовок `X-Role`).

---

## Архитектура

* **Backend**: FastAPI (`/api`: upload/forecast/scenario/advice/report/pdf/backtest/dev/seed).
* **Frontend**: Streamlit (дашборд: прогноз, сценарии, совет, экспорт, backtest).
* **LLM**: локальный **Ollama**, **OpenAI-совместимые** endpoint’ы (например, **vLLM** или **Groq**).
* **Хранилище артефактов**: `data/processed/` (Parquet при наличии `pyarrow`, иначе CSV fallback).

---

## Структура репозитория

```
liquidity-assistant/
├─ infra/
│  ├─ docker-compose.yml
│  └─ nginx.conf
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ routers/ (upload, forecast, scenario, advice, reports, backtest, llm_test, dev_seed, sources)
│  │  ├─ services/ (etl, features, forecast, scenarios, advisor, llm, reports, backtest)
│  │  ├─ core/ (config, logging, auth)
│  │  ├─ models/schemas.py
│  │  └─ utils/ (validators, io)
│  ├─ tests/
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ app.py
│  ├─ pages/ (Overview, Scenarios, Reports, Backtest)
│  ├─ requirements.txt
│  └─ Dockerfile
├─ shai_workflow/ (бонус: workflow.yaml + agents/*.yaml)
├─ data/
│  └─ sample/ (bank_statements.csv, payment_calendar.csv, fx_rates.csv)
├─ scripts/ (generate_mock_data.py, backtest.py, export_pdf.py, run_pipeline.sh)
├─ docs/ (architecture.md, api.md, pitch_script.md, shai_workflow.md)
└─ .env.example
```

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
python -m streamlit run app.py
```

Открой: `http://127.0.0.1:8501`

### Docker Compose

```bash
cd infra
docker compose up --build
```

* Frontend: `http://localhost:8501` (или через Nginx: `http://localhost:8080`)
* Backend: `http://localhost:8000` (Swagger: `/docs`)

---

## Конфигурация (.env)

Скопируйте `.env.example` → `backend/.env` **или** используйте переменные окружения (Compose их прокидывает).

```env
# LLM (варианты ниже)
LLM_PROVIDER=ollama                  # ollama | openai | (пусто = без LLM)
LLM_MODEL=qwen2.5:7b-instruct-q4_K_M # пример для Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434

# OpenAI-совместимые (vLLM/Groq)
OPENAI_BASE_URL=http://your-vllm-host:8001/v1
OPENAI_API_KEY=any_token

# Таймауты/параметры
LLM_TIMEOUT=60

# Scheduler (опц.)
SYNC_EVERY_MIN=0

# FX пары по умолчанию (для sources, если используется)
FX_PAIRS=USD/KZT,EUR/KZT
```

> **RBAC**: запросы к API должны передавать заголовок `X-Role` (`Analyst`, `Treasurer`, `CFO`). См. раздел [RBAC](#rbac-роли).

---

## LLM-провайдеры (Ollama / vLLM / Groq)

### Ollama (off-the-shelf на ноуте)

```bash
brew install --cask ollama
ollama pull qwen2.5:7b-instruct-q4_K_M
```

`.env`:

```
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b-instruct-q4_K_M
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

### vLLM (он-прем / сервер)

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3.1-8B-Instruct \
  --host 0.0.0.0 --port 8001 --max-model-len 8192
```

`.env`:

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://your-vllm-host:8001/v1
OPENAI_API_KEY=any_token
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Groq (OpenAI-совместимый SaaS)

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=sk_groq_********************************
LLM_MODEL=llama-3.3-70b-versatile   # пример
```

Проверка:

```
GET /api/llm/test
```

Ответ содержит `ok`, `provider`, `model`, `base_url`, `sample`.

---

## Демо-данные и CSV-схемы

### Генерация синтетики (для быстрого демо)

```
POST /api/dev/seed   (X-Role: Analyst)
```

Создаёт витрину `daily_cash` и базовые CSV в `data/processed/`.

### Схемы CSV

**bank\_statements.csv**

```
date,account,currency,amount
2025-08-01,MAIN,KZT,200000
2025-08-01,MAIN,USD,-1000
```

**payment\_calendar.csv**

```
date,type,currency,amount,memo
2025-08-03,inflow,KZT,500000,Client invoice
2025-08-07,outflow,KZT,650000,Payroll
```

**fx\_rates.csv**

```
date,USD/KZT,EUR/KZT
2025-08-01,500,540
2025-08-02,501,539.5
```

Загрузка трёх файлов:

```
POST /api/upload   (multipart/form-data, files=[...])
```

---

## API (FastAPI)

Базовый префикс: `/api` • Swagger: `/docs`

* `GET /api/health` — статус API
* `GET /api/llm/test` — статус LLM
* `POST /api/upload` — загрузка CSV (bank/payment/fx)
* `POST /api/forecast` — `{ "horizon_days": 14, "scenario": "baseline|stress|optimistic" }`
* `POST /api/scenario` — `{"horizon_days":14,"fx_shock":0.1,"delay_top_inflow_days":0,"delay_top_outflow_days":0}`
* `POST /api/advice` — `{ "baseline": {...}, "scenario": {...} }` → текст брифа + actions
* `POST /api/report/pdf` — принимает baseline/scenario/advice, возвращает PDF
* `POST /api/backtest` — rolling backtest (MAPE/sMAPE), сравнение моделей
* `POST /api/dev/seed` — сидер синтетики (для демо)

Примеры запросов/ответов — см. `docs/api.md`.

---

## Фронтенд (Streamlit)

* Сайдбар: `API URL`, индикаторы статуса **API/LLM**.
* «Базовый прогноз»: выбор горизонта и **сценария** (`baseline/stress/optimistic`).
* «Сценарии»: FX-шок и задержки поступлений/выплат.
* «Совет»: LLM-бриф + действия; показывает **красные дни** и даты рисков.
* «Экспорт брифа»: Markdown + кнопка **Скачать PDF**.
* «Backtest»: rolling window, таблица метрик, график факт vs прогноз, выгрузка CSV/JSON.

---

## Отчёты PDF

`POST /api/report/pdf` — формирует бриф CFO (ReportLab).
Для кириллицы используются шрифты **DejaVu**. Если PDF «кракозябрами»:

* убедитесь, что файлы `DejaVuSans*.ttf` доступны бэкенду (в Docker — примонтированы в `backend/app/assets/fonts`);
* используемый шрифт в коде: `"DejaVuSans"` / `"DejaVuSans-Bold"`.

---

## Backtest & сравнение моделей

Страница **04\_Backtest** + эндпоинт `POST /api/backtest`:

* rolling origin, параметры: `horizon`, `window`, `step`, `target_col`, `models`.
* модели: `naive_last`, `naive_mean`, `arima` (pmdarima), `prophet` (опц., если установлен).
* метрики: **MAPE**, **sMAPE**, график факт vs средний прогноз по датам.
* выгрузка summary (CSV) и per-model (JSON).
* офлайн-скрипт: `python scripts/backtest.py --horizon 7 --window 30 --models naive_last,arima`.

---

## RBAC (роли)

Роли передаются заголовком `X-Role`:

* `/forecast`, `/scenario`, `/backtest`, `/dev/seed` → `Analyst` (или выше)
* `/advice`, `/report/pdf` → `CFO`/`Treasurer`

При 403 — проверьте заголовок. Для демо можно ослабить проверки в `core/auth.py`.

---

## Инфра / Nginx / Healthchecks

Compose (см. `infra/docker-compose.yml`):

* сервисы: `backend`, `frontend`, (опц.) `nginx`;
* healthchecks: `backend → /api/health`, `frontend → /_stcore/health`;
* фронту передаётся `API_URL=http://backend:8000/api`;
* тома: `../data/processed` (артефакты), `../backend/app/assets/fonts` (шрифты для PDF).

Опц. Nginx (`infra/nginx.conf`): роутинг `/` → фронт, `/api` → бэкенд.

---

## Скрипты и тесты

* `scripts/generate_mock_data.py` — синтетика
* `scripts/backtest.py` — офлайн-бэктест
* `scripts/export_pdf.py` — рендер PDF из JSON
* `backend/tests/*` — `pytest`:

  ```bash
  cd backend && pytest -q
  ```

---

## Shai Workflow (бонус)

В `shai_workflow/` есть `workflow.yaml` и `agents/*.yaml` — описание сквозного пайплайна **Data → Forecast → Scenario → Advisor → Report** для внешнего оркестратора (HTTP-узлы). Подробности: `docs/shai_workflow.md`.

---

## Траблшутинг

* **403 forbidden**: проверьте `X-Role`.
* **/api/upload → 400**: проверьте имена/схемы CSV и кодировку (UTF-8).
* **Нет Parquet**: установите `pyarrow` или используйте CSV fallback (авто).
* **LLM: Connection refused**: проверьте `LLM_PROVIDER/BASE_URL/API_KEY`, эндпоинт `/api/llm/test`.
* **PDF «кракозябры»**: примонтируйте шрифты `DejaVu` и проверьте, что ReportLab их видит.
* **Backtest пуст**: возможно, мало истории (`window + horizon`) — уменьшите параметры.

---

## Лицензия

MIT — см. `LICENSE`.

