import os
import json
import io
import pandas as pd
import streamlit as st
import requests

st.set_page_config(page_title="Отчёты", layout="wide")
api_base = os.getenv("API_URL", "http://127.0.0.1:8000/api")

st.title("Экспорт и отчёты")
st.caption("Экспортируем краткий бриф в Markdown. PDF-генерация можно добавить позже через эндпоинт /reports на бэкенде.")

baseline = st.text_area("Вставьте JSON из /forecast (опционально)")
scenario = st.text_area("Вставьте JSON из /scenario (опционально)")

if st.button("Сформировать совет из JSON"):
    try:
        bl = json.loads(baseline) if baseline.strip() else {}
        sc = json.loads(scenario) if scenario.strip() else {}
        payload = {"baseline": bl, "scenario": sc}
        r = requests.post(f"{api_base}/advice", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        st.subheader("Совет")
        st.write(data.get("advice_text"))
        st.subheader("Действия")
        acts = data.get("actions", [])
        if acts:
            st.dataframe(pd.DataFrame(acts))
        md = io.StringIO()
        md.write("# Liquidity Assistant — Бриф\n\n")
        md.write(data.get("advice_text","") + "\n")
        if acts:
            md.write("\n## Действия\n")
            for a in acts:
                md.write(f"- {a.get('title')} — ~{a.get('amount')} ({a.get('rationale')})\n")
        st.download_button("Скачать бриф.md", md.getvalue().encode("utf-8"), file_name="liquidity_brief.md")
    except Exception as e:
        st.error(str(e))
