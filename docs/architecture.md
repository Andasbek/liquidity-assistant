
# `docs/architecture.md`

```markdown
# Liquidity Assistant — Архитектура

## Цели
- Быстрый MVP для прогноза ежедневной ликвидности, what-if сценариев и краткого брифа для CFO.
- Простая локальная разработка и демонстрация (Streamlit + FastAPI).
- Возможность масштабировать: заменить модели, добавить БД, отчёты PDF, роли.

## Обзор
**Frontend**: Streamlit  
**Backend**: FastAPI  
**ETL/Storage**: локальная витрина `data/processed/daily_cash.(parquet|csv)`  
**LLM**: Ollama или OpenAI-совместимый endpoint  
**PDF**: ReportLab (встроенная генерация, кириллица — DejaVuSans)

```

User ⇄ Streamlit (frontend)
⇄ FastAPI (backend)
├─ ETL: CSV → daily\_cash
├─ Forecast: pmdarima → fallback
├─ Scenario: FX shock, delays
├─ Advisor: rules + LLM
└─ Reports: PDF (ReportLab)

```

## Данные и витрины
### Входные CSV
- `bank_statements.csv`: `date, account, currency, amount` (+ inflow, − outflow)
- `payment_calendar.csv`: `date, type[inflow|outflow], currency, amount, memo`
- `fx_rates.csv`: `date, USD/KZT, EUR/KZT, ...` (ffill/bfill по валютам)

### Витрина `daily_cash`
Колонки: `date, net_cash, cash_balance`  
- `net_cash` — агрегированный нетто-поток за день (после нормализации банка и платёжного календаря, учёта FX)  
- `cash_balance` — кумулятивная сумма (от нуля/начала ряда)

## Модули backend
```

app/
├─ main.py                # FastAPI, CORS, APScheduler (опц.), роутеры
├─ routers/
│  ├─ upload.py           # POST /api/upload
│  ├─ forecast.py         # POST /api/forecast
│  ├─ scenario.py         # POST /api/scenario
│  ├─ advice.py           # POST /api/advice (RBAC: CFO/Treasurer)
│  ├─ reports.py          # POST /api/report/pdf
│  └─ llm\_test.py         # GET /api/llm/test
├─ core/
│  ├─ config.py           # .env, провайдер LLM, таймауты, синк
│  └─ auth.py             # require\_any(...), X-Role
├─ models/schemas.py      # Pydantic схемы
├─ services/
│  ├─ etl.py              # normalize(), build\_daily\_cashframe()
│  ├─ forecast.py         # pmdarima | naive; sMAPE; apply scenario
│  ├─ scenarios.py        # FX shock, задержки inflow/outflow
│  ├─ advisor.py          # правила + LLM бриф (fallback)
│  └─ reports.py          # PDF отчет (ReportLab + DejaVuSans)
└─ utils/
├─ io.py               # parquet/csv save/load (fallback)
└─ validators.py       # валидация CSV/дат

```

## Прогноз
- Модель: `pmdarima.auto_arima`; если недоступна или мало данных — наивный (последнее значение).
- Метрика: sMAPE (ин-сэмпл по one-step-naive).
- Сценарии: масштабирование будущих `net_cash` (`baseline|stress|optimistic`).

## Сценарии (What-if)
- `fx_shock`: коэффициент к положительным `net_cash` (имитация FX-выручки).
- `delay_top_inflow_days`: перенос максимального дня притока на N дней вперёд.
- `delay_top_outflow_days`: перенос минимального дня оттока на N дней вперёд.
- После изменений пересчёт `cash_balance`.

## Advisor (LLM)
- Правила:
  - min_cash < 0 → «ККЛ +10% буфер»
  - высокий средний остаток на хвосте → «депозит 60%»
- LLM-сводка: system-prompt + JSON контекст → короткий бриф (RU).  
- Fallback без LLM: краткий текст по правилам.

## Отчёты (PDF)
- ReportLab, страницы A4, кириллица через DejaVuSans.
- Разделы: «Прогноз и метрики», «Рекомендации», «Действия».
- Таблицы с переносами (Paragraph в ячейках).

## Безопасность и роли
- RBAC через заголовок `X-Role`: `Analyst`/`Treasurer`/`CFO`.  
- `/advice` и `/report/pdf` обычно требуют CFO/Treasurer (конфигурируемо).

## Развёртывание
- Локально: `uvicorn app.main:app --reload`, Streamlit — `streamlit run app.py`.
- Docker Compose: `infra/docker-compose.yml` (backend, frontend, опц. nginx).
- LLM: Ollama (локально) или OpenAI-совместимые (vLLM и т.п.).

## Роадмап
- Расширить backtest (rolling) и сравнение моделей (Prophet/LightGBM).
- БД: Postgres + Alembic, авторизация (JWT/SSO).
- Рассылки PDF и мониторинг (Prometheus/Grafana).
```

---



---

