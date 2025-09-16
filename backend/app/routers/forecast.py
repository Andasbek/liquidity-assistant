from fastapi import APIRouter, HTTPException
from ..models.schemas import ForecastRequest, ForecastResponse
from ..services import forecast as svc_forecast
from ..utils.io import load_df

router = APIRouter(tags=["forecast"])

@router.post("/forecast", response_model=ForecastResponse)
def make_forecast(req: ForecastRequest):
    try:
        daily = load_df("daily_cash.parquet")
    except FileNotFoundError:
        raise HTTPException(400, detail="Upload data first via /upload")

    fcst, metrics = svc_forecast.forecast_cash(daily, req.horizon_days)
    return ForecastResponse(forecast=fcst, metrics=metrics)
