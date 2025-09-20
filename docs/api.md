# `docs/api.md`

````markdown
# Liquidity Assistant — API

Базовый URL: `http://localhost:8000/api`  
Аутентификация: RBAC по заголовку `X-Role` (`Analyst`, `Treasurer`, `CFO`)

## Health
`GET /health` → `{"status":"ok"}`

`GET /llm/test` → информация о провайдере/модели и пробный ответ.

---

## Загрузка данных
### `POST /upload`
Форм-дата (multipart):
- `files=@bank_statements.csv`
- `files=@payment_calendar.csv`
- `files=@fx_rates.csv`

Ответ:
```json
{"loaded":{"bank_statements.csv":123,"payment_calendar.csv":45,"fx_rates.csv":60,"daily_cash.parquet":61}}
````

Ошибки: `400` при несоответствии схем/кодировке.

---

## Прогноз

### `POST /forecast`

Заголовок: `X-Role: Analyst | Treasurer | CFO`

Тело:

```json
{ "horizon_days": 14, "scenario": "baseline" }
```

Ответ:

```json
{
  "forecast": [
    {"date":"2025-09-20","net_cash":10000.0,"cash_balance":123456.0},
    ...
  ],
  "metrics": {"smape": 12.34},
  "scenario": "baseline"
}
```

---

## Сценарии

### `POST /scenario`

Заголовок: `X-Role: Analyst | Treasurer | CFO`

Тело:

```json
{
  "horizon_days": 14,
  "scenario": "stress",
  "fx_shock": 0.1,
  "delay_top_inflow_days": 7,
  "delay_top_outflow_days": 0
}
```

Ответ:

```json
{
  "forecast_scenario": [...],
  "min_cash": -250000.0,
  "metrics": {"smape": 12.34},
  "scenario": "stress"
}
```

---

## Совет (Advisor)

### `POST /advice`

Заголовок: `X-Role: CFO | Treasurer`

Тело:

```json
{
  "baseline": { "forecast": [...], "metrics": {...} },
  "scenario": { "forecast_scenario": [...], "min_cash": -250000.0, "metrics": {...} }
}
```

Ответ:

```json
{
  "advice_text": "Краткий бриф...",
  "actions": [
    {"title":"Открыть ККЛ","amount":275000.0,"rationale":"..."}
  ]
}
```

Ошибки: `403 forbidden` при недостаточной роли; `400` если отсутствует витрина.

---

## PDF-отчёт

### `POST /report/pdf`

Заголовок: `X-Role: CFO | Treasurer | Analyst` (настраивается)

Тело:

```json
{
  "baseline": {...},     // ответ /forecast
  "scenario": {...},     // ответ /scenario
  "advice":   {...},     // ответ /advice
  "horizon_days": 14
}
```

Ответ: `application/pdf` (attachment: `liquidity_brief.pdf`)

---

## Коды ошибок

* `400` — неверный запрос/данные не загружены.
* `403` — роль не допускается.
* `404` — роут не найден.
* `500` — внутренняя ошибка (смотреть логи).

````