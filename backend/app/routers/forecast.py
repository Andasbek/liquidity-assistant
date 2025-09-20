from fastapi import APIRouter, Depends
from ..core.auth import require_any
from ..models.schemas import ForecastRequest, ForecastResponse
from ..services.forecast import get_forecast

router = APIRouter(tags=["forecast"])  # ← без prefix

@router.post(
    "/forecast",
    response_model=ForecastResponse,
    dependencies=[Depends(require_any("CFO", "Treasurer", "Analyst"))],
)
def forecast_api(payload: ForecastRequest):
    fcst, metrics = get_forecast(
        horizon=payload.horizon_days,
        scenario=payload.scenario or "baseline",
    )
    return ForecastResponse(forecast=fcst, metrics=metrics, scenario=payload.scenario or "baseline")
