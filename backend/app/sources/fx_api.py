from datetime import date, timedelta
import os
import httpx
import pandas as pd
import numpy as np

FX_PAIRS_DEFAULT = os.getenv("FX_PAIRS", "USD/KZT,EUR/KZT").split(",")

EXCHANGERATE_HOST = "https://api.exchangerate.host/timeseries"  # общедоступный
FX_BASE_CCY = "KZT"  # приводим к KZT

def _timeseries_exchangeratehost(start: date, end: date, pairs=None) -> pd.DataFrame:
    """
    Возвращает датафрейм вида: date, USD/KZT, EUR/KZT ...
    exchangerate.host отдаёт base=, symbols=; приведём к формату XXX/KZT.
    """
    pairs = pairs or FX_PAIRS_DEFAULT
    symbols = ",".join(sorted({p.split("/")[0] for p in pairs if p.endswith("/KZT")}))
    params = {
        "start_date": start.isoformat(),
        "end_date":   end .isoformat(),
        "base":       FX_BASE_CCY,
        "symbols":    symbols,
        "places":     4,
    }
    with httpx.Client(timeout=30) as client:
        r = client.get(EXCHANGERATE_HOST, params=params)
        r.raise_for_status()
        data = r.json()
    rates = data.get("rates", {})
    rows = []
    for ds, daily in rates.items():
        # daily: {"USD": rate_in_KZT? => т.к. base=KZT, символы - иностранные валюты,
        # нам нужен XXX/KZT => инверсия 1/daily[XXX] (if daily[XXX] != 0)
        row = {"date": pd.to_datetime(ds)}
        for p in pairs:
            ccy = p.split("/")[0]
            v = daily.get(ccy)
            if v and v != 0:
                row[f"{ccy}/KZT"] = round(1/float(v), 4)  # XXX/KZT
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("date")
    # ffill/bfill по парам
    for p in pairs:
        if p not in df.columns:
            df[p] = np.nan
        df[p] = df[p].ffill().bfill()
    df["date"] = df["date"].dt.date
    return df[["date"] + pairs]

def fetch_fx_rates(start: date, end: date, pairs=None) -> pd.DataFrame:
    """
    Пытаемся получить курсы из публичного API, при ошибке — синтетика (random walk).
    """
    try:
        return _timeseries_exchangeratehost(start, end, pairs=pairs)
    except Exception:
        # синтетика как fallback
        pairs = pairs or FX_PAIRS_DEFAULT
        days = (end - start).days + 1
        dates = [start + timedelta(days=i) for i in range(days)]
        np.random.seed(42)
        base = {"USD/KZT": 500.0, "EUR/KZT": 540.0}
        data = {"date": dates}
        for p in pairs:
            series = [base.get(p, 500.0)]
            for _ in range(1, days):
                series.append(series[-1] + np.random.normal(0, 0.8))
            data[p] = np.round(series, 2)
        return pd.DataFrame(data)
