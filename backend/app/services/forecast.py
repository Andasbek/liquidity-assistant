import pandas as pd
import numpy as np
from typing import Tuple, Dict, List

# пытаемся использовать pmdarima; если нет — fallback на наивный прогноз
try:
    import pmdarima as pm
    HAS_PMD = True
except Exception:
    HAS_PMD = False

def _naive_forecast(series: pd.Series, horizon: int) -> List[float]:
    last = float(series.iloc[-1]) if len(series) else 0.0
    return [last] * horizon

def forecast_cash(daily: pd.DataFrame, horizon_days: int) -> Tuple[list, Dict[str, float]]:
    """
    Прогнозируем net_cash на горизонте и на его основе считаем будущий cash_balance.
    Возвращаем список точек {date, net_cash, cash_balance} и метрики (sMAPE).
    """
    df = daily.copy().sort_values("date")
    df["date"] = pd.to_datetime(df["date"])
    series = df["net_cash"].astype(float)

    if HAS_PMD and len(series) >= 14:
        try:
            model = pm.auto_arima(series, seasonal=False, suppress_warnings=True, stepwise=True)
            yhat = model.predict(n_periods=horizon_days).tolist()
        except Exception:
            yhat = _naive_forecast(series, horizon_days)
    else:
        yhat = _naive_forecast(series, horizon_days)

    # строим будущие даты (дневной шаг, пропуская выходные НЕ нужно — касса считается по датам)
    last_date = df["date"].iloc[-1]
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")

    # будущий баланс = последний баланс + кумсум прогноза
    last_balance = float(df["cash_balance"].iloc[-1]) if len(df) else 0.0
    fut_cum = np.cumsum(yhat) + last_balance

    out = []
    for d, nc, bal in zip(future_dates, yhat, fut_cum):
        out.append({"date": d.date().isoformat(), "net_cash": float(nc), "cash_balance": float(bal)})

    # простая метрика sMAPE по walk-forward (если данных хватает)
    metrics = {"smape": float(_smape(series.values, _insample_naive(series)))}
    return out, metrics

def _insample_naive(series: pd.Series) -> np.ndarray:
    # предыдущий день как прогноз (one-step ahead) — для грубой sMAPE
    if len(series) < 2:
        return np.zeros_like(series.values)
    pred = np.r_[series.values[0], series.values[:-1]]
    return pred

def _smape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom)) * 100.0
