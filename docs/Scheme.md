liquidity-assistant/
├─ infra/
│  ├─ docker-compose.yml
│  └─ nginx.conf                     # (при желании) реверс-прокси для фронта/апи
├─ backend/
│  ├─ app/
│  │  ├─ main.py                     # точка входа FastAPI
│  │  ├─ routers/
│  │  │  ├─ upload.py               # POST /upload: csv -> parquet, валидация
│  │  │  ├─ forecast.py             # POST /forecast: окна, horizon, модель
│  │  │  ├─ scenario.py             # POST /scenario: what-if (FX, задержки)
│  │  │  └─ advice.py               # POST /advice: правила + LLM-бриф
│  │  ├─ core/
│  │  │  ├─ config.py               # env, пути, горизонты, валюты
│  │  │  └─ logging.py              # единые логи, json формат
│  │  ├─ models/
│  │  │  └─ schemas.py              # Pydantic: Payloads/Responses
│  │  ├─ services/
│  │  │  ├─ etl.py                  # загрузка/очистка/джойны csv
│  │  │  ├─ features.py             # агрегаты по дням, нетто-потоки
│  │  │  ├─ forecast.py             # ARIMA/Prophet baseline, backtest
│  │  │  ├─ scenarios.py            # шоки курса, сдвиги платежей
│  │  │  ├─ advisor.py              # правила ликвидности + LLM-формулировка
│  │  │  └─ reports.py              # pdf/md отчёт CFO с графиками
│  │  └─ utils/
│  │     ├─ validators.py           # проверки csv, схем, дат
│  │     └─ io.py                   # сохранение/чтение parquet, кэши
│  ├─ tests/
│  │  ├─ test_etl.py
│  │  ├─ test_forecast.py
│  │  └─ test_scenarios.py
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ app.py                         # Streamlit дашборд (Cash, Forecast, What-if)
│  ├─ pages/
│  │  ├─ 01_Overview.py             # сводка ликвидности
│  │  ├─ 02_Scenarios.py            # слайдеры сценариев и сравнение
│  │  └─ 03_Reports.py              # экспорт PDF, истории расчётов
│  ├─ components/                    # (опц.) кастомные виджеты
│  ├─ requirements.txt
│  └─ Dockerfile
├─ shai_workflow/                    # бонус: low-code сценарий для shai.pro
│  ├─ workflow.yaml                  # оркестрация агентов
│  └─ agents/
│     ├─ DataAgent.yaml
│     ├─ ForecastAgent.yaml
│     ├─ ScenarioAgent.yaml
│     ├─ AdvisorAgent.yaml
│     └─ ReportAgent.yaml
├─ data/
│  └─ sample/
│     ├─ bank_statements.csv         # дата, счёт, валюта, сумма(+/−)
│     ├─ payment_calendar.csv        # обязательства/поступления, даты, суммы
│     └─ fx_rates.csv                # дата, USD/KZT, EUR/KZT …
├─ scripts/
│  ├─ generate_mock_data.py          # синтетика для демо
│  ├─ backtest.py                    # rolling backtest, метрики MAPE/sMAPE
│  └─ export_pdf.py                  # рендер CFO-брифа из json → PDF
├─ notebooks/
│  └─ eda_forecast.ipynb             # быстрый EDA и sanity-чек модели
├─ docs/
│  ├─ architecture.md                # схема слоёв, данные, метрики
│  ├─ api.md                         # OpenAPI эндпоинты и примеры тел
│  └─ pitch_script.md                # текст 3–5-мин видеопитча (сценарий)
├─ .env.example
├─ .gitignore
└─ README.md
