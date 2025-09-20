# backend/app/services/scenarios.py
from __future__ import annotations
from typing import Dict
from uuid import uuid4

from .forecast import get_forecast
from .scenarios_utils import points_to_df, df_to_points, apply_scenarios_safe

def run_scenario(
    horizon_days: int = 35,
    scenario: str = "baseline",
    fx_shock: float = 0.0,
    delay_top_inflow_days: int = 0,
    delay_top_outflow_days: int = 0,
    shift_purchases_days: int = 0,  # опционально: можно сделать отдельный перенос для «закупок»
):
    base_points, _ = get_forecast(horizon=horizon_days, scenario=scenario)
    base_df = points_to_df(base_points)

    # стартовый баланс = B0 из baseline ряда
    if not base_df.empty:
        b0 = float(base_df.iloc[0]["cash_balance"]) - float(base_df.iloc[0]["net_cash"])
    else:
        b0 = 0.0

    scen_df = apply_scenarios_safe(
        base_df[["date", "net_cash", "cash_balance"]],
        base_balance0=b0,
        fx_shock=fx_shock,
        delay_top_inflow_days=delay_top_inflow_days,
        delay_top_outflow_days=delay_top_outflow_days,
    )

    pts = df_to_points(scen_df)
    min_cash = min((p["cash_balance"] for p in pts), default=0.0)

    return {
        "run_id": str(uuid4()),
        "scenario": scenario,
        "forecast_scenario": pts,
        "min_cash": float(min_cash),
        "metrics": None,
    }
