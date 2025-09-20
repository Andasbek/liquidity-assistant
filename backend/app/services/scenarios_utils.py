# backend/app/services/scenarios_utils.py
from __future__ import annotations
import pandas as pd
from typing import List, Dict, Optional
from datetime import date

def points_to_df(points: List[Dict]) -> pd.DataFrame:
    if not points:
        return pd.DataFrame(columns=["date", "net_cash", "cash_balance"])
    df = pd.DataFrame(points).copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()  # к полуночи
    df["net_cash"] = pd.to_numeric(df["net_cash"], errors="coerce").fillna(0.0)
    if "cash_balance" in df.columns:
        df["cash_balance"] = pd.to_numeric(df["cash_balance"], errors="coerce")
    return df[["date", "net_cash", "cash_balance"]].sort_values("date").reset_index(drop=True)

def df_to_points(df: pd.DataFrame) -> List[Dict]:
    if df.empty:
        return []
    out = []
    for _, r in df.sort_values("date").iterrows():
        out.append({
            "date": r["date"].date() if isinstance(r["date"], pd.Timestamp) else r["date"],
            "net_cash": float(r["net_cash"]),
            "cash_balance": float(r["cash_balance"]),
        })
    return out

def apply_scenarios_safe(
    daily: pd.DataFrame,
    *,
    base_balance0: Optional[float] = None,
    fx_shock: float = 0.0,
    delay_top_inflow_days: int = 0,
    delay_top_outflow_days: int = 0,
) -> pd.DataFrame:
    """
    Устойчивое применение сценариев:
      - агрегирует по дате перед операциями,
      - FX-шок применяем только к положительным net_cash,
      - переносит max inflow / min outflow на указанное число дней,
      - корректно инициализирует cash_balance с учётом исходного баланса.
    """
    if daily is None or daily.empty:
        return pd.DataFrame(columns=["date", "net_cash", "cash_balance"])

    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["net_cash"] = pd.to_numeric(df["net_cash"], errors="coerce").fillna(0.0)

    # 0) Агрегируем по дню (если были дубли строк на дату)
    df = df.groupby("date", as_index=False, sort=True)["net_cash"].sum()

    # 1) FX-шок — к положительным дням (MVP-модель)
    if fx_shock:
        pos = df["net_cash"] > 0
        df.loc[pos, "net_cash"] = df.loc[pos, "net_cash"] * (1.0 + fx_shock)

    # 2) Переносы
    df = _delay_extreme_daily(df, is_inflow=True, days=delay_top_inflow_days)
    df = _delay_extreme_daily(df, is_inflow=False, days=delay_top_outflow_days)

    # 3) Баланс: старт — либо явно передан, либо из исходных данных
    if base_balance0 is None:
        # если был cash_balance в исходном daily — возьмём его из последней фактической точки:
        if "cash_balance" in daily.columns and not daily["cash_balance"].isna().all():
            # восстановим B0 = B_t - net_t на первой дате ряда
            first = daily.sort_values("date").iloc[0]
            try:
                base_balance0 = float(first["cash_balance"]) - float(first["net_cash"])
            except Exception:
                base_balance0 = 0.0
        else:
            base_balance0 = 0.0

    # 4) Перерасчёт баланса
    df = df.sort_values("date").reset_index(drop=True)
    bal = float(base_balance0)
    cash_col = []
    for v in df["net_cash"].tolist():
        bal += float(v)
        cash_col.append(bal)
    df["cash_balance"] = cash_col

    return df[["date", "net_cash", "cash_balance"]]


def _delay_extreme_daily(df: pd.DataFrame, *, is_inflow: bool, days: int) -> pd.DataFrame:
    """Переносит экстремум (max inflow / min outflow) на N дней вперёд, сохраняя агрегированность по дню."""
    if not days or df.empty:
        return df

    # гарантируем типы
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    d["net_cash"] = pd.to_numeric(d["net_cash"], errors="coerce").fillna(0.0)

    # выбираем дату-экстремум (при равенстве берём более раннюю)
    if is_inflow:
        extremum_val = d["net_cash"].max()
        if pd.isna(extremum_val) or extremum_val <= 0:
            return d
        pick = d.loc[d["net_cash"].idxmax()]
    else:
        extremum_val = d["net_cash"].min()
        if pd.isna(extremum_val) or extremum_val >= 0:
            return d
        pick = d.loc[d["net_cash"].idxmin()]

    src_date = pd.to_datetime(pick["date"]).normalize()
    amount = float(pick["net_cash"])
    dst_date = src_date + pd.Timedelta(days=days)

    # вычитаем сумму на исходной дате, добавляем на целевой, затем ре-агрегируем
    d.loc[d["date"] == src_date, "net_cash"] = d.loc[d["date"] == src_date, "net_cash"] - amount
    # добавить строку целевой даты
    d = pd.concat([d, pd.DataFrame({"date": [dst_date], "net_cash": [amount]})], ignore_index=True)
    # на всякий — нормализуем по дню
    d = d.groupby("date", as_index=False, sort=True)["net_cash"].sum()
    return d
