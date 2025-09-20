# backend/app/services/scenarios.py
from __future__ import annotations
from typing import List, Dict
from uuid import uuid4
from datetime import timedelta
from copy import deepcopy

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse


from ..core.auth import require_any
from ..models.schemas import ScenarioRequest
from ..services.scenarios import run_scenario

from ..services.forecast import get_forecast  # используем твой baseline
from ..models.schemas import ScenarioResponse  # если не хочешь pydantic — можно вернуть dict

router = APIRouter(tags=["scenario"])

@router.post("/scenario", response_model=ScenarioResponse,
             dependencies=[Depends(require_any("CFO", "Treasurer", "Analyst"))])
def scenario_api(payload: ScenarioRequest):
    # run_scenario принимает именованные аргументы — распакуем pydantic-модель
    return run_scenario(**payload.model_dump())


def _apply_fx_shock(points: List[Dict], fx_shock: float) -> List[Dict]:
    """Грубая аппроксимация влияния FX: масштабируем net_cash на (1+shock)."""
    if not fx_shock:
        return points
    out = []
    bal = 0.0
    # пересчёт баланса заново от первого значения
    # начнём от текущего первого баланса, если он есть
    bal = points[0]["cash_balance"] - points[0]["net_cash"]
    for p in points:
        net = float(p["net_cash"]) * (1.0 + fx_shock)
        bal += net
        out.append({"date": p["date"], "net_cash": net, "cash_balance": bal})
    return out


def _delay_extreme(points: List[Dict], positive: bool, delay_days: int) -> List[Dict]:
    """Сдвигаем самый крупный inflow/outflow на delay_days вперёд."""
    if delay_days <= 0 or not points:
        return points

    idx = None
    best = None
    for i, p in enumerate(points):
        val = p["net_cash"]
        if positive:
            if val > 0 and (best is None or val > best):
                best, idx = val, i
        else:
            if val < 0 and (best is None or val < best):
                best, idx = val, i
    if idx is None:
        return points

    out = deepcopy(points)
    target = min(len(points) - 1, idx + delay_days)
    # переносим сумму: на исходном дне зануляем, на целевом добавляем
    moved = out[idx]["net_cash"]
    out[idx]["net_cash"] = 0.0
    out[target]["net_cash"] += moved

    # пересоберём баланс
    bal = out[0]["cash_balance"] - out[0]["net_cash"]
    for p in out:
        bal += p["net_cash"]
        p["cash_balance"] = bal
    return out


def _shift_purchases(points: List[Dict], days: int) -> List[Dict]:
    """Упрощённо: сдвигаем самый большой по модулю outflow на days вперёд (похоже на delay_top_outflow)."""
    if days <= 0:
        return points
    return _delay_extreme(points, positive=False, delay_days=days)


def run_scenario(
    horizon_days: int = 35,
    scenario: str = "baseline",
    fx_shock: float = 0.0,
    delay_top_inflow_days: int = 0,
    delay_top_outflow_days: int = 0,
    shift_purchases_days: int = 0,
) -> ScenarioResponse:
    """
    Главный вход для /api/scenario.
    1) Берём baseline/stress/optimistic прогноз.
    2) Применяем FX-шок как масштаб к net_cash.
    3) Сдвигаем крупнейшие inflow/outflow (delay_*).
    4) Доп. «сдвиг закупок» (shift_purchases_days) как перенос крупнейшего outflow.
    """
    base_points, _ = get_forecast(horizon=horizon_days, scenario=scenario)

    pts = _apply_fx_shock(base_points, fx_shock)
    if delay_top_inflow_days:
        pts = _delay_extreme(pts, positive=True, delay_days=delay_top_inflow_days)
    if delay_top_outflow_days:
        pts = _delay_extreme(pts, positive=False, delay_days=delay_top_outflow_days)
    if shift_purchases_days:
        pts = _shift_purchases(pts, days=shift_purchases_days)

    # min_cash и простые метрики
    min_cash = min(p["cash_balance"] for p in pts) if pts else 0.0
    run_id = str(uuid4())

    # Можно вернуть dict, FastAPI сам приведёт к pydantic-схеме.
    return ScenarioResponse(
        run_id=run_id,
        scenario=scenario,
        forecast_scenario=pts,
        min_cash=min_cash,
        metrics=None,
    )
