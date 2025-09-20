# backend/app/services/forecast.py
from __future__ import annotations
from typing import Tuple, Dict, List
from datetime import timedelta

import numpy as np
import pandas as pd

# пытаемся использовать pmdarima; если нет — fallback на наивный прогноз
try:
    import pmdarima as pm
    HAS_PMD = True
except Exception:
    HAS_PMD = False

# локальные импорты из проекта
from ..utils.io import load_df
from ..core import config


# -------------------------
# Вспомогательные функции
# -------------------------

def _load_daily_cash_df() -> pd.DataFrame:
    """Возвращает витрину daily_cash.* как DataFrame (или пустой DF с нужными колонками)."""
    df = None
    for name in ("daily_cash", "daily_cash.parquet", "daily_cash.csv"):
        try:
            df = load_df(name)
            break
        except FileNotFoundError:
            continue
    if df is None:
        return pd.DataFrame(columns=["date", "net_cash", "cash_balance"])
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["net_cash"] = pd.to_numeric(df["net_cash"], errors="coerce").fillna(0.0)
    if "cash_balance" in df.columns:
        df["cash_balance"] = pd.to_numeric(df["cash_balance"], errors="coerce").fillna(0.0)
    else:
        # на всякий — если нет колонки, восстановим от нуля
        df = df.sort_values("date")
        df["cash_balance"] = df["net_cash"].cumsum()
    return df.sort_values("date")


def _naive_forecast(series: pd.Series, horizon: int) -> List[float]:
    last = float(series.iloc[-1]) if len(series) else 0.0
    return [last] * int(horizon)

def _insample_naive(series: pd.Series) -> np.ndarray:
    if len(series) < 2:
        return np.zeros_like(series.values, dtype=float)
    return np.r_[series.values[0], series.values[:-1]]

def _smape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom)) * 100.0

# -------------------------
# Основная логика прогноза
# -------------------------

def forecast_cash(daily: pd.DataFrame, horizon_days: int) -> Tuple[List[Dict], Dict[str, float]]:
    """
    Строит прогноз ТОЛЬКО будущих точек [{date, net_cash, cash_balance}] и метрики (sMAPE).
    Гарантированно возвращает (list, dict).
    """
    # аккуратно создаём df
    if daily is None:
        df = pd.DataFrame(columns=["date", "net_cash", "cash_balance"])
    else:
        df = daily.copy()

    if df.empty:
        last_date = pd.Timestamp.today().normalize()
        last_balance = 0.0
        yhat = [0.0] * int(horizon_days)
        metrics = {"smape": float("nan")}
    else:
        df = df.sort_values("date")
        df["date"] = pd.to_datetime(df["date"])
        df["net_cash"] = pd.to_numeric(df["net_cash"], errors="coerce").fillna(0.0)
        if "cash_balance" in df.columns:
            df["cash_balance"] = pd.to_numeric(df["cash_balance"], errors="coerce").fillna(0.0)
        series = df["net_cash"].astype(float)

        if HAS_PMD and len(series) >= 14:
            try:
                model = pm.auto_arima(series, seasonal=False, suppress_warnings=True, stepwise=True)
                yhat = model.predict(n_periods=int(horizon_days)).tolist()
            except Exception:
                yhat = _naive_forecast(series, int(horizon_days))
        else:
            yhat = _naive_forecast(series, int(horizon_days))

        last_date = pd.to_datetime(df["date"].iloc[-1])
        last_balance = float(df["cash_balance"].iloc[-1]) if "cash_balance" in df.columns else 0.0
        metrics = {"smape": float(_smape(series.values, _insample_naive(series)))}

    # будущие даты и баланс
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=int(horizon_days), freq="D")
    fut_cum = (np.cumsum(yhat) + last_balance).astype(float)

    out: List[Dict] = []
    for d, nc, bal in zip(future_dates, yhat, fut_cum):
        out.append({"date": d.date().isoformat(), "net_cash": float(nc), "cash_balance": float(bal)})

    return out, metrics


def _apply_scenario(points: List[Dict], last_balance: float, scenario: str) -> List[Dict]:
    factor = 1.0
    s = (scenario or "baseline").lower()
    if s == "stress":
        factor = 0.95
    elif s == "optimistic":
        factor = 1.05

    out: List[Dict] = []
    bal = float(last_balance)
    for p in points:
        net = float(p["net_cash"]) * factor
        bal += net
        out.append({"date": p["date"], "net_cash": net, "cash_balance": bal})
    return out

def get_forecast(horizon: int | None = None, scenario: str = "baseline") -> Tuple[List[Dict], Dict]:
    if horizon is None or horizon <= 0:
        horizon = int(getattr(config, "DEFAULT_HORIZON_DAYS", 35))

    df = _load_daily_cash_df()
    fut_points, metrics = forecast_cash(df, horizon_days=horizon)
    last_balance = float(df["cash_balance"].iloc[-1]) if not df.empty else 0.0
    fut_points = _apply_scenario(fut_points, last_balance, scenario)

    return fut_points, metrics
