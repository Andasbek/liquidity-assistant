# frontend/pages/04_Backtest.py
import io
import json
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Backtest & Models", page_icon="📈", layout="wide")

# --- API base ---------------------------------------------------------------
api_base = (st.session_state.get("API_URL") or "http://127.0.0.1:8000/api").rstrip("/")

def api_post(path: str, json_data=None, role: str = "Analyst", timeout: int = 60):
    url = api_base + ("/" + path.lstrip("/"))
    try:
        r = requests.post(url, json=json_data or {}, headers={
            "Content-Type": "application/json",
            "X-Role": role
        }, timeout=timeout)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = r.text
            return None, f"{r.status_code} {r.reason} — {detail}"
        return r.json(), None
    except requests.RequestException as e:
        return None, str(e)

# --- UI ---------------------------------------------------------------------
st.title("📈 Backtest & сравнение моделей")

with st.sidebar:
    st.header("Параметры")
    role = st.selectbox("Роль (RBAC)", ["Analyst", "Treasurer", "CFO"], index=0)
    horizon = st.number_input("Горизонт (дней)", 1, 60, 7, 1)
    window = st.number_input("Мин. длина истории (дней)", 7, 180, 30, 1)
    step = st.number_input("Шаг окна", 1, 14, 1, 1)
    target_col = st.selectbox("Целевая серия", ["net_cash"])
    models = st.multiselect("Модели", ["naive_last", "naive_mean", "arima", "prophet"],
                            default=["naive_last", "arima"])
    run_btn = st.button("Запустить backtest", type="primary")

# хранение последнего результата для скачивания/повтора
if "backtest_result" not in st.session_state:
    st.session_state["backtest_result"] = None

def fmt_pct(x):
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "—"

def df_safe(records):
    try:
        df = pd.DataFrame(records or [])
        # нормализуем date, если есть
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

if run_btn:
    with st.spinner("Считаем…"):
        payload = {
            "horizon": int(horizon),
            "window": int(window),
            "step": int(step),
            "target_col": target_col,
            "models": models,
        }
        data, err = api_post("/backtest", json_data=payload, role=role)
    if err:
        st.error(f"Ошибка: {err}")
    else:
        st.session_state["backtest_result"] = data
        st.success("Готово ✅")

data = st.session_state["backtest_result"]

if not data:
    st.info("Задайте параметры в сайдбаре и нажмите «Запустить backtest».")
    st.stop()

# --- Summary ---------------------------------------------------------------
st.subheader("🏁 Итоговые метрики")
df_sum = df_safe(data.get("summary"))
if df_sum.empty:
    st.info("Нет данных для метрик (возможно, мало истории).")
else:
    # карточки по топ-3
    top = df_sum.sort_values("sMAPE").head(3).reset_index(drop=True)
    cols = st.columns(len(top))
    for i, row in top.iterrows():
        with cols[i]:
            st.metric(
                label=f"Модель: {row.get('model','—')}",
                value=fmt_pct(row.get("sMAPE")),
                delta=f"MAPE {fmt_pct(row.get('MAPE'))}"
            )
    st.dataframe(df_sum, use_container_width=True)

# --- Per-model chart --------------------------------------------------------
st.subheader("📊 Факт vs прогноз")
per_model = data.get("per_model") or {}
opts = [m for m in per_model.keys() if per_model[m]]
if not opts:
    st.info("Нет результатов per-model.")
else:
    model_sel = st.selectbox("Модель", opts, index=0)
    dfm = df_safe(per_model.get(model_sel))
    if dfm.empty:
        st.info("Недостаточно точек для графика.")
    else:
        dfm = dfm.sort_values("date")
        # группируем по дате, если перекрываются окна
        g = dfm.groupby("date", as_index=False).agg({"y_true": "mean", "y_pred": "mean"})
        g = g.set_index("date")
        st.line_chart(g[["y_true", "y_pred"]])
        with st.expander("Показать сырые точки (пересечения окон)"):
            st.dataframe(dfm, use_container_width=True)

# --- Downloads --------------------------------------------------------------
st.subheader("⬇️ Экспорт результатов")
colA, colB = st.columns(2)
with colA:
    # summary CSV
    if not df_sum.empty:
        csv_sum = df_sum.to_csv(index=False).encode("utf-8")
        st.download_button("Скачать summary (CSV)", data=csv_sum, file_name="backtest_summary.csv",
                           mime="text/csv", use_container_width=True)
with colB:
    # per-model JSON
    json_bytes = json.dumps(per_model, ensure_ascii=False).encode("utf-8")
    st.download_button("Скачать per-model (JSON)", data=json_bytes, file_name="backtest_per_model.json",
                       mime="application/json", use_container_width=True)
