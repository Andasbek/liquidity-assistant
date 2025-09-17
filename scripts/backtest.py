#!/usr/bin/env python
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT  = ROOT / "data" / "reports"
OUT.mkdir(parents=True, exist_ok=True)

def smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denom = (np.abs(y_true) + np.abs(y_pred))
    denom[denom == 0] = 1e-9
    return (100.0 / len(y_true)) * np.sum(np.abs(y_pred - y_true) / denom)

def mae(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return float(np.mean(np.abs(y_pred - y_true)))

def rolling_forecast_naive(series, horizon, window=7):
    """
    Наивный прогноз: среднее скользящее по последним window для net_cash,
    cash_balance как cumsum(net_cash).
    """
    preds = []
    hist = list(series)  # список значений net_cash
    for _ in range(horizon):
        w = hist[-window:] if len(hist) >= window else hist
        pred = float(np.mean(w)) if len(w) else 0.0
        preds.append(pred)
        hist.append(pred)
    return preds

def main(horizon=14, window=7, start_offset=30):
    # daily_cash: date, net_cash, cash_balance
    df = None
    for name in ("daily_cash.parquet", "daily_cash.csv"):
        p = DATA / name
        if p.exists():
            df = pd.read_parquet(p) if name.endswith(".parquet") else pd.read_csv(p)
            break
    if df is None or df.empty:
        raise SystemExit("daily_cash.* not found or empty")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    metrics = []
    # скользящее окно: начиная с start_offset (чтобы было на что учиться)
    for i in range(start_offset, len(df) - horizon):
        hist = df.iloc[:i]
        future = df.iloc[i:i+horizon]

        # прогнозируем net_cash
        preds_net = rolling_forecast_naive(hist["net_cash"].values, horizon=horizon, window=window)
        # считаем баланс: берем последний факт баланса + cumsum(preds_net)
        last_balance = float(hist["cash_balance"].values[-1]) if len(hist) else 0.0
        preds_bal = np.cumsum(preds_net) + last_balance

        # метрики по net_cash
        m_smape = smape(future["net_cash"].values, preds_net)
        m_mae   = mae  (future["net_cash"].values, preds_net)

        # сигнал о кассовом разрыве в прогнозе
        forecast_min_bal = float(np.min(preds_bal))
        warn_predicted = forecast_min_bal < 0

        # случится ли отрицательный баланс фактически в горизонте?
        true_bal = hist["cash_balance"].values[-1] + np.cumsum(future["net_cash"].values)
        true_min_bal = float(np.min(true_bal))
        event_true = true_min_bal < 0

        # насколько заранее модель "подняла флаг"?
        days_to_event = None
        if event_true:
            # день наступления разрыва в факте
            day_event_idx = int(np.where(true_bal < 0)[0][0])
            # была ли точка в preds_bal, где ушло <0 до day_event_idx?
            alert_idx = next((k for k, v in enumerate(preds_bal) if v < 0), None)
            if alert_idx is not None:
                days_to_event = max(0, day_event_idx - alert_idx)

        metrics.append({
            "asof": df["date"].iloc[i-1].date().isoformat(),
            "horizon": horizon,
            "smape": round(m_smape, 3),
            "mae": round(m_mae, 3),
            "forecast_min_balance": round(forecast_min_bal, 2),
            "warn_predicted": bool(warn_predicted),
            "true_min_balance": round(true_min_bal, 2),
            "event_true": bool(event_true),
            "days_to_event_early": (int(days_to_event) if days_to_event is not None else None),
        })

    met_df = pd.DataFrame(metrics)
    met_path = OUT / "backtest_metrics.csv"
    met_df.to_csv(met_path, index=False)

    # короткий итог
    agg = {
        "runs": len(met_df),
        "smape_mean": round(float(met_df["smape"].mean()), 3),
        "mae_mean": round(float(met_df["mae"].mean()), 3),
        "early_warnings": int(met_df["warn_predicted"].sum()),
        "events_true": int(met_df["event_true"].sum()),
        "median_days_to_event_early": float(met_df["days_to_event_early"].dropna().median()) if met_df["days_to_event_early"].notna().any() else None
    }
    print("Backtest summary:", agg)

    # картинка: распределение sMAPE
    plt.figure(figsize=(6,4))
    plt.hist(met_df["smape"].values, bins=20)
    plt.title("sMAPE distribution (net_cash forecast)")
    plt.xlabel("sMAPE, %")
    plt.ylabel("count")
    img_path = OUT / "backtest_smape_hist.png"
    plt.savefig(img_path, bbox_inches="tight", dpi=150)
    print("Saved:", met_path, img_path)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=14)
    ap.add_argument("--window",  type=int, default=7)
    ap.add_argument("--offset",  type=int, default=30, help="минимальная длина истории до первого прогноза")
    args = ap.parse_args()
    main(horizon=args.horizon, window=args.window, start_offset=args.offset)
