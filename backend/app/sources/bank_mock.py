from datetime import date, timedelta
import numpy as np
import pandas as pd

def pull_bank_statements(start: date, end: date) -> pd.DataFrame:
    """
    Мок-адаптер банка: генерит 0–3 операций в день по KZT/USD.
    """
    np.random.seed(123)
    dates = pd.date_range(start, end, freq="D").date
    rows = []
    for d in dates:
        for _ in range(np.random.randint(0, 4)):
            ccy = np.random.choice(["KZT", "USD"], p=[0.7, 0.3])
            sign = np.random.choice([1, -1], p=[0.55, 0.45])
            amt  = np.random.choice([200_000, 350_000, 500_000, 800_000, 1_200_000, 2_000_000])
            rows.append({"date": d, "account": "MAIN", "currency": ccy, "amount": float(sign*amt)})
    return pd.DataFrame(rows)

def pull_payment_calendar(start: date, end: date) -> pd.DataFrame:
    """
    Мок-платёжный календарь: еженедельные inflow, раз в 2 недели payroll, иногда USD outflow.
    """
    dates = pd.date_range(start, end, freq="D").date
    rows = []
    for i, d in enumerate(dates):
        if i % 7 == 0:
            rows.append({"date": d, "type": "inflow",  "currency": "KZT", "amount": 5_000_000, "memo": "Client invoice"})
        if i % 14 == 0:
            rows.append({"date": d, "type": "outflow", "currency": "KZT", "amount": 6_500_000, "memo": "Payroll"})
        if i % 21 == 5:
            rows.append({"date": d, "type": "outflow", "currency": "USD", "amount": 20_000,   "memo": "Import"})
    return pd.DataFrame(rows)
