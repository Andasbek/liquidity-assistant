# backend/app/services/backtest.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from ..utils.io import load_df

# опционально pmdarima
try:
    import pmdarima as pm
    HAS_PMD = True
except Exception:
    HAS_PMD = False

# опционально Prophet
try:
    from prophet import Prophet  # pip install prophet
    HAS_PROPHET = True
except Exception:
    HAS_PROPHET = False


# ========= метрики =========

def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom) * 100.0)


# ========= модели =========

def _fc_naive_last(series: pd.Series, h: int) -> List[float]:
    last = float(series.iloc[-1]) if len(series) else 0.0
    return [last] * h

def _fc_naive_mean(series: pd.Series, h: int) -> List[float]:
    mean = float(series.mean()) if len(series) else 0.0
    return [mean] * h

def _fc_arima(series: pd.Series, h: int) -> List[float]:
    if not HAS_PMD or len(series) < 8:
        return _fc_naive_last(series, h)
    try:
        model = pm.auto_arima(series, seasonal=False, suppress_warnings=True, stepwise=True)
        return model.predict(n_periods=h).tolist()
    except Exception:
        return _fc_naive_last(series, h)

def _fc_prophet(series: pd.Series, index: pd.DatetimeIndex, h: int) -> List[float]:
    if not HAS_PROPHET or len(series) < 12:
        return _fc_naive_last(series, h)
    df = pd.DataFrame({"ds": index, "y": series.astype(float).values})
    try:
        m = Prophet(seasonality_mode="additive", weekly_seasonality=True, daily_seasonality=False)
        m.fit(df)
        future = m.make_future_dataframe(periods=h, freq="D", include_history=False)
        yhat = m.predict(future)["yhat"].values.tolist()
        return yhat
    except Exception:
        return _fc_naive_last(series, h)

MODEL_FUNCS = {
    "naive_last": _fc_naive_last,
    "naive_mean": _fc_naive_mean,
    "arima": _fc_arima,
    "prophet": _fc_prophet,  # сработает только если установлен prophet
}


@dataclass
class BacktestParams:
    horizon: int = 7
    window: int = 30          # минимальная длина обучающей истории
    step: int = 1             # шаг окна (rolling origin)
    target_col: str = "net_cash"
    use_models: Optional[List[str]] = None  # если None — все доступные


def load_daily_cash() -> pd.DataFrame:
    # читаем витрину
    for name in ("daily_cash", "daily_cash.parquet", "daily_cash.csv"):
        try:
            df = load_df(name)
            break
        except FileNotFoundError:
            continue
    else:
        raise FileNotFoundError("daily_cash.* not found. Upload data first.")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def rolling_backtest(params: BacktestParams) -> Dict:
    df = load_daily_cash()
    y = pd.to_numeric(df[params.target_col], errors="coerce").fillna(0.0)
    idx = pd.to_datetime(df["date"])

    models = params.use_models or list(MODEL_FUNCS.keys())
    # отфильтруем модели по доступности либ
    if "prophet" in models and not HAS_PROPHET:
        models = [m for m in models if m != "prophet"]

    results: Dict[str, Dict] = {}
    per_model_rows = {m: [] for m in models}

    # rolling origin
    n = len(y)
    start = params.window
    h = int(params.horizon)
    step = int(params.step)

    for m in models:
        fc_func = MODEL_FUNCS[m]
        # для Prophet нужен индекс
        for t in range(start, n - h + 1, step):
            train_series = y.iloc[:t]
            train_index = idx.iloc[:t]
            # прогноз на h вперёд
            if m == "prophet":
                yhat = fc_func(train_series, train_index, h)
            else:
                yhat = fc_func(train_series, h)

            # «истина»
            y_true = y.iloc[t : t + h].values
            dates = idx.iloc[t : t + h].values

            # метрики на этом блоке
            block_mape = mape(y_true, yhat)
            block_smape = smape(y_true, yhat)

            # копим строки
            for d, yt, yp in zip(dates, y_true, yhat):
                per_model_rows[m].append({
                    "date": pd.to_datetime(d),
                    "y_true": float(yt),
                    "y_pred": float(yp),
                    "model": m,
                })

        # агрегированные метрики по всем блокам
        dfm = pd.DataFrame(per_model_rows[m])
        dfm = dfm.sort_values("date")
        # сравниваем по датам, где есть и факт, и прогноз
        if not dfm.empty:
            merged = dfm.merge(
                df[["date", params.target_col]].rename(columns={params.target_col: "y_true_full"}),
                on="date", how="left"
            )
            merged["abs_perc"] = np.where(
                merged["y_true_full"] != 0,
                np.abs((merged["y_true_full"] - merged["y_pred"]) / merged["y_true_full"]),
                np.nan
            )
            metrics = {
                "MAPE": float(np.nanmean(merged["abs_perc"]) * 100.0),
                "sMAPE": smape(merged["y_true_full"].values, merged["y_pred"].values),
                "points": int(len(merged)),
            }
        else:
            metrics = {"MAPE": float("nan"), "sMAPE": float("nan"), "points": 0}

        results[m] = {
            "metrics": metrics,
            "detail": pd.DataFrame(per_model_rows[m]),
        }

    # сводка
    summary = []
    for m, r in results.items():
        summary.append({
            "model": m,
            "MAPE": r["metrics"]["MAPE"],
            "sMAPE": r["metrics"]["sMAPE"],
            "points": r["metrics"]["points"],
        })
    summary_df = pd.DataFrame(summary).sort_values("sMAPE")

    return {
        "summary": summary_df,
        "per_model": {m: d["detail"] for m, d in results.items()},
        "params": vars(params),
    }
