import os
import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Сценарии", layout="wide")
api_base = os.getenv("API_URL", "http://127.0.0.1:8000/api")

st.title("Сценарии 'what-if' — быстрый тест")
st.caption("Та же логика, что и на главной, но в отдельной странице для чистого эксперимента.")

horizon = st.slider("Горизонт (дней)", 7, 60, 14, 1)
fx_shock = st.number_input("Шок FX (0.1 = +10%)", value=0.05, step=0.05, format="%.2f")
d_in = st.number_input("Задержка крупнейшего inflow (дн.)", value=0, min_value=0, max_value=30)
d_out = st.number_input("Задержка крупнейшего outflow (дн.)", value=0, min_value=0, max_value=30)

if st.button("Применить"):
    payload = {
        "horizon_days": int(horizon),
        "fx_shock": float(fx_shock),
        "delay_top_inflow_days": int(d_in),
        "delay_top_outflow_days": int(d_out),
    }
    try:
        r = requests.post(f"{api_base}/scenario", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        pts = data.get("forecast_scenario", [])
        if not pts:
            st.warning("Нет точек в ответе.")
        else:
            df = pd.DataFrame(pts)
            df["date"] = pd.to_datetime(df["date"])
            fig, ax = plt.subplots(figsize=(10,4))
            ax.plot(df["date"], df["cash_balance"], label="Cash balance")
            ax.bar(df["date"], df["net_cash"], alpha=0.3, label="Net cash (bar)")
            ax.set_title("Сценарий: Cash balance")
            ax.legend()
            st.pyplot(fig)
        st.json({"min_cash": data.get("min_cash"), "metrics": data.get("metrics")})
    except Exception as e:
        st.error(str(e))
