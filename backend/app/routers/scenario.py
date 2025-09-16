from fastapi import APIRouter, HTTPException
from ..models.schemas import ScenarioRequest, ScenarioResponse
from ..services import scenarios as svc_scen, forecast as svc_forecast
from ..utils.io import load_df

router = APIRouter(tags=["scenario"])

@router.post("/scenario", response_model=ScenarioResponse)
def apply_scenario(req: ScenarioRequest):
    try:
        daily = load_df("daily_cash.parquet")
    except FileNotFoundError:
        raise HTTPException(400, detail="Upload data first via /upload")

    shocked = svc_scen.apply_scenarios(
        daily, fx_shock=req.fx_shock,
        delay_top_inflow_days=req.delay_top_inflow_days,
        delay_top_outflow_days=req.delay_top_outflow_days
    )
    fcst, metrics = svc_forecast.forecast_cash(shocked, req.horizon_days)
    min_cash = float((shocked["cash_balance"]).min()) if "cash_balance" in shocked else None
    return ScenarioResponse(forecast_scenario=fcst, min_cash=min_cash, metrics=metrics)
