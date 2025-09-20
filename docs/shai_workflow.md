# shai\_workflow — оркестрация пайплайна (бонус из ТЗ)

Этот модуль — необязательная надстройка над API. Он описывает **сквозной сценарий** в виде YAML-workflow и «агентов», которые по шагам вызывают ваши REST-эндпоинты:

**Data → Forecast → Scenario → Advisor → Report (PDF)**

Подходит для:

* автодемо/прогона без UI;
* интеграции с внешним оркестратором/раннером (low-code);
* регламентных запусков (по расписанию).

> Если оркестратора нет — см. раздел «Без оркестратора (curl)».

---

## Структура

```
shai_workflow/
├─ workflow.yaml            # сценарий из шагов
└─ agents/
   ├─ DataAgent.yaml        # POST /api/dev/seed (опц.)
   ├─ ForecastAgent.yaml    # POST /api/forecast
   ├─ ScenarioAgent.yaml    # POST /api/scenario
   ├─ AdvisorAgent.yaml     # POST /api/advice
   └─ ReportAgent.yaml      # POST /api/report/pdf → base64 PDF
```

* **workflow\.yaml** — «режиссёр»: переменные, входные параметры, порядок шагов, прокидка результатов между шагами.
* **agents/\*.yaml** — «исполнители»: что вызвать (URL, метод, заголовки), какое тело запроса сформировать, что вернуть дальше.

---

## Входные параметры и переменные

В `workflow.yaml` уже определены типичные параметры:

```yaml
variables:
  API_BASE:     # адрес API
    default: "http://backend:8000/api"
  ROLE_CFO:
    default: "CFO"
  ROLE_ANALYST:
    default: "Analyst"

inputs:
  horizon_days:                # горизонт прогноза
    type: integer
    default: 14
  scenario_name:               # baseline|stress|optimistic (пример)
    type: string
    default: "stress"
  fx_shock:
    type: number
    default: 0.10
  delay_top_inflow_days:
    type: integer
    default: 0
  delay_top_outflow_days:
    type: integer
    default: 0
  seed_demo_data:              # сгенерировать синтетику для демо
    type: boolean
    default: true
```

Меняйте `API_BASE`, если запускаете вне docker-compose:

* локально: `http://localhost:8000/api`
* в compose: `http://backend:8000/api`

---

## Логика шагов

1. **DataAgent** (опционально)
   Если `seed_demo_data=true`, дергает `POST /api/dev/seed` и создаёт витрину `daily_cash` из синтетики.

2. **ForecastAgent**
   `POST /api/forecast` с `horizon_days`. Возвращает `forecast[]` и `metrics`.

3. **ScenarioAgent**
   `POST /api/scenario` с `scenario`, `fx_shock`, задержками. Возвращает `forecast_scenario[]`, `min_cash`, `metrics`.

4. **AdvisorAgent**
   `POST /api/advice`, на вход — результаты forecast+scenario. Возвращает `advice_text` и `actions[]`.

5. **ReportAgent**
   `POST /api/report/pdf`, на вход — baseline, scenario, advice. Возвращает **PDF** (в вашем раннере — обычно в base64).

Итоговые `outputs` содержат ключевые показатели (sMAPE, min\_cash, число действий) и `pdf_base64`.

---

## Запуск в оркестраторе

Зависит от конкретного инструмента (shai.pro, n8n, Airflow с YAML-плагином и т.п.). Общая схема:

1. Указать корень проекта с `workflow.yaml` и папкой `agents/`.
2. Подставить `variables.API_BASE` (если нужно).
3. Запустить пайплайн с нужными `inputs` (по умолчанию можно не задавать).

Результатом будет объект с:

* `summary` (метрики/итоги),
* `pdf_base64` (строка PDF).

---

## Без оркестратора (curl)

Эквивалентный сквозной прогон вручную:

```bash
# 1) (опц.) демо-данные
curl -X POST -H "X-Role: Analyst" http://localhost:8000/api/dev/seed

# 2) forecast
FC=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: Analyst" \
  -d '{"horizon_days":14}' http://localhost:8000/api/forecast)

# 3) scenario
SC=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: Analyst" \
  -d '{"horizon_days":14,"scenario":"stress","fx_shock":0.1}' http://localhost:8000/api/scenario)

# 4) advice
AD=$(jq -n --argjson b "$FC" --argjson s "$SC" '{baseline:$b, scenario:$s}')
ADV=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: CFO" \
  -d "$AD" http://localhost:8000/api/advice)

# 5) pdf
PDF_PAYLOAD=$(jq -n --argjson b "$FC" --argjson s "$SC" --argjson a "$ADV" \
  '{baseline:$b,scenario:$s,advice:$a,"horizon_days":14}')
curl -s -X POST -H "Content-Type: application/json" -H "X-Role: CFO" \
  -d "$PDF_PAYLOAD" http://localhost:8000/api/report/pdf > liquidity_brief.pdf
```

> Требуется `jq`. Если его нет — сформируйте тела вручную из файлов.

---

## RBAC и заголовки

Агенты прокидывают роли через заголовок `X-Role`:

* `/forecast`, `/scenario` → `Analyst` (или выше),
* `/advice`, `/report/pdf` → `CFO`/`Treasurer`.

Если вы сменили роли в `core/auth.py`, обновите значения в `workflow.yaml`.

---

## Типичные ошибки и решения

* **403 forbidden**
  Проверьте заголовок `X-Role` и права на роут.

* **400 /api/upload / dev/seed**
  Нет витрины `daily_cash` — либо загрузите CSV, либо включите `seed_demo_data=true`.

* **PDF кракозябры**
  Убедитесь, что в контейнер примонтированы шрифты DejaVu (`backend/app/assets/fonts`) и что `reports.py` задаёт `FONTNAME` в таблицах.

* **Нет Prophet/pmdarima**
  Бэктест/forecast автоматически откатятся на наивные модели. Чтобы включить Prophet — установите `prophet`. Для ARIMA — `pmdarima`.

---

## Изменение сценария

Хотите другой порядок шагов или дополнительную ветку (например, несколько сценариев подряд)?
Редактируйте `steps` в `workflow.yaml`: добавляйте новые шаги с нужным агентом и прокидывайте нужные поля через `outputs` → `inputs` следующих шагов.

---

## Зачем хранить этот модуль в репозитории?

* Документирует **сквозной процесс** (полезно для команды/стейкхолдеров).
* Готовая «кнопка» для автодемо и интеграций.
* Легко расширяется без изменения бэка/фронта: это только описания HTTP-шагов.
