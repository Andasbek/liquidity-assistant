import os
import json
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Обзор", layout="wide")

st.title("Обзор данных (витрина daily_cash)")
st.caption("Показывает собранный дневной нетто-поток и баланс (если бэкенд уже построил витрину).")

api_base = os.getenv("API_URL", "http://127.0.0.1:8000/api")

st.info("В этой версии страница только информативная. Витрина формируется после /upload на бэке. Для просмотра графиков — используйте главную страницу.")

st.markdown(
"""
**Что важно проверить руками перед демо:**
- даты без пропусков
- нет ли экстремальных выбросов в `net_cash`
- корректно ли накапливается `cash_balance` (кумулятив)
"""
)
