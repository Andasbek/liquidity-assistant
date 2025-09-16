import os
import json
import io
import requests
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

# ---- Config ----
DEFAULT_API = os.getenv("API_URL", "http://127.0.0.1:8000/api")
st.set_page_config(page_title="Liquidity Assistant", layout="wide")


# ---- Sidebar Settings ----
st.sidebar.header("Настройки")
api_base = st.sidebar.text_input("API URL", value=DEFAULT_API, help="Адрес FastAPI, например http://127.0.0.1:8000/api")
horizon = st.sidebar.slider("Горизонт прогноза (дней)", 7, 60, 14, 1)

import requests

def safe_get_json(url: str):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

st.markdown("### Статус подключения")
col_h, col_l = st.columns(2)
with col_h:
    data, err = safe_get_json(f"{api_base}/health")
    if err or not data or data.get("status") != "ok":
        st.error(f"API: нет связи ({err or data})")
    else:
        st.success("API: OK")
with col_l:
    data, err = safe_get_json(f"{api_base}/llm/test")
    if err or not data:
        st.warning(f"LLM: нет связи ({err})")
    else:
        prov = data.get("provider") or "—"
        sample = data.get("sample") or ""
        if prov and not sample.startswith("error"):
            st.success(f"LLM: {prov} — готово")
        else:
            st.warning(f"LLM: есть конфиг, но ответ пустой/ошибка ({sample[:60]})")

st.sidebar.markdown("---")
st.sidebar.write("**Файлы входных данных** (CSV):")
uploaded_bank = st.sidebar.file_uploader("bank_statements.csv", type=["csv"])
uploaded_pay = st.sidebar.file_uploader("payment_calendar.csv", type=["csv"])
uploaded_fx  = st.sidebar.file_uploader("fx_rates.csv", type=["csv"])
upload_btn = st.sidebar.button("Загрузить в бекенд")

# ---- Session state ----
if "forecast" not in st.session_state:
    st.session_state["forecast"] = None
if "scenario" not in st.session_state:
    st.session_state["scenario"] = None
if "baseline_resp" not in st.session_state:
    st.session_state["baseline_resp"] = None
if "scenario_resp" not in st.session_state:
    st.session_state["scenario_resp"] = None
if "advice" not in st.session_state:
    st.session_state["advice"] = None

# ---- Helpers ----
def api_post(path: str, files=None, json_data=None):
    url = f"{api_base}{path}"
    try:
        if files:
            resp = requests.post(url, files=files, timeout=60)
        else:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, data=json.dumps(json_data or {}), headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json(), None
    except requests.RequestException as e:
        if getattr(e, "response", None) is not None:
            try:
                return None, f"{e} — {e.response.text}"
            except Exception:
                return None, str(e)
        return None, str(e)

def plot_forecast(forecast_points: list, title: str):
    if not forecast_points:
        st.info("Нет данных для графика.")
        return
    df = pd.DataFrame(forecast_points)
    df["date"] = pd.to_datetime(df["date"])
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["date"], df["cash_balance"], label="Cash balance")
    ax.bar(df["date"], df["net_cash"], alpha=0.3, label="Net cash (bar)")
    ax.set_title(title)
    ax.set_xlabel("Дата")
    ax.set_ylabel("Сумма, KZT")
    ax.legend()
    st.pyplot(fig)
    return df

# ---- Upload ----
if upload_btn:
    if not (uploaded_bank and uploaded_pay and uploaded_fx):
        st.sidebar.error("Загрузите все три файла CSV.")
    else:
        files = [
                ("files", ("bank_statements.csv", uploaded_bank.getvalue(), "text/csv")),
                ("files", ("payment_calendar.csv", uploaded_pay.getvalue(), "text/csv")),
                ("files", ("fx_rates.csv", uploaded_fx.getvalue(), "text/csv"))
            ]
        data, err = api_post("/upload", files=files)
        if err:
            st.sidebar.error(f"Ошибка загрузки: {err}")
        else:
            st.sidebar.success(f"Загружено: {data.get('loaded')}")
            # очищаем старые расчеты после новой загрузки
            st.session_state["forecast"] = None
            st.session_state["scenario"] = None
            st.session_state["baseline_resp"] = None
            st.session_state["scenario_resp"] = None
            st.session_state["advice"] = None

st.title("💧 Liquidity Assistant — Дашборд")

# ---- Forecast Section ----
st.header("1) Базовый прогноз ликвидности")
colF1, colF2 = st.columns([1, 1])

with colF1:
    if st.button("Сделать прогноз", type="primary"):
        payload = {"horizon_days": horizon}
        resp, err = api_post("/forecast", json_data=payload)
        if err:
            st.error(f"Ошибка прогноза: {err}")
        else:
            st.session_state["forecast"] = resp.get("forecast")
            st.session_state["baseline_resp"] = resp
            st.success("Готово — прогноз посчитан.")
            plot_forecast(st.session_state["forecast"], "Базовый прогноз Cash balance (горизонт)")

with colF2:
    if st.session_state["baseline_resp"]:
        m = st.session_state["baseline_resp"].get("metrics", {})
        st.subheader("Метрики качества (черновые)")
        st.write({k: round(v, 3) for k, v in m.items()})

# ---- Scenario Section ----
st.header("2) Сценарии 'what-if'")
colS1, colS2, colS3, colS4 = st.columns(4)
with colS1:
    fx_shock = st.number_input("Шок FX (доля, напр. 0.1 = +10%)", value=0.10, step=0.05, format="%.2f")
with colS2:
    d_in = st.number_input("Задержка крупнейшего inflow (дн.)", value=0, min_value=0, max_value=30, step=1)
with colS3:
    d_out = st.number_input("Задержка крупнейшего outflow (дн.)", value=0, min_value=0, max_value=30, step=1)
with colS4:
    st.write("")  # spacer
    run_scenario = st.button("Применить сценарий", type="secondary")

if run_scenario:
    payload = {
        "horizon_days": horizon,
        "fx_shock": fx_shock,
        "delay_top_inflow_days": int(d_in),
        "delay_top_outflow_days": int(d_out),
    }
    resp, err = api_post("/scenario", json_data=payload)
    if err:
        st.error(f"Ошибка сценария: {err}")
    else:
        st.session_state["scenario"] = resp.get("forecast_scenario")
        st.session_state["scenario_resp"] = resp
        st.success("Сценарий рассчитан.")
        plot_forecast(st.session_state["scenario"], "Сценарий: Cash balance при шоках")

# ---- Advice Section ----
st.header("3) Совет по действиям (Advisor)")
colA1, colA2 = st.columns([1, 1])
with colA1:
    if st.button("Сформировать совет"):
        if not (st.session_state["baseline_resp"] and st.session_state["scenario_resp"]):
            st.warning("Сначала посчитайте базовый прогноз и сценарий.")
        else:
            payload = {
                "baseline": st.session_state["baseline_resp"],
                "scenario": st.session_state["scenario_resp"]
            }
            resp, err = api_post("/advice", json_data=payload)
            if err:
                st.error(f"Ошибка совета: {err}")
            else:
                st.session_state["advice"] = resp
                st.success("Совет сформирован.")

with colA2:
    if st.session_state["advice"]:
        st.subheader("Текст совета")
        st.write(st.session_state["advice"].get("advice_text", ""))

        st.subheader("Действия")
        actions = st.session_state["advice"].get("actions", [])
        if actions:
            st.dataframe(pd.DataFrame(actions))
        else:
            st.info("Действий нет — рисков не обнаружено.")

# ---- Download Brief (Markdown) ----
st.header("4) Экспорт краткого брифа (Markdown)")
if st.session_state["baseline_resp"] or st.session_state["scenario_resp"] or st.session_state["advice"]:
    brief = io.StringIO()
    brief.write("# Liquidity Assistant — Бриф для CFO\n\n")
    if st.session_state["baseline_resp"]:
        brief.write("## Базовый прогноз\n")
        m = st.session_state["baseline_resp"].get("metrics", {})
        brief.write(f"- sMAPE: {round(m.get('smape', 0.0), 3)}\n")
    if st.session_state["scenario_resp"]:
        brief.write("\n## Сценарий\n")
        brief.write(f"- min_cash: {st.session_state['scenario_resp'].get('min_cash', 'N/A')}\n")
        m2 = st.session_state["scenario_resp"].get("metrics", {})
        brief.write(f"- sMAPE (scenario): {round(m2.get('smape', 0.0), 3)}\n")
    if st.session_state["advice"]:
        brief.write("\n## Совет\n")
        brief.write(st.session_state["advice"].get("advice_text", "") + "\n")
        acts = st.session_state["advice"].get("actions", [])
        if acts:
            brief.write("\n### Действия\n")
            for a in acts:
                brief.write(f"- {a.get('title')} — ~{a.get('amount')} ({a.get('rationale')})\n")

    st.download_button("Скачать бриф.md", brief.getvalue().encode("utf-8"), file_name="liquidity_brief.md", mime="text/markdown")
else:
    st.info("После расчётов вы сможете экспортировать бриф.")
