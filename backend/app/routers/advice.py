# backend/app/routers/advice.py
from fastapi import APIRouter, Depends
from ..core.auth import require_any
from ..models.schemas import AdviceRequest, AdviceResponse
from ..services.advisor import build_advice

router = APIRouter(tags=["advice"])  # без prefix="/api" — он в main.py

@router.post(
    "/advice",
    response_model=AdviceResponse,
    dependencies=[Depends(require_any("CFO", "Treasurer"))],
)
def advice_api(payload: AdviceRequest):
    """
    Принимает:
      {
        "baseline": { "forecast": [...], "metrics": {...}, ... },
        "scenario": { "forecast_scenario": [...], "min_cash": ..., ... }
      }
    Возвращает AdviceResponse с текстом брифа и actions.
    """
    return build_advice(payload)
