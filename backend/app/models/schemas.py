from pydantic import BaseModel, Field, conint, confloat
from datetime import date
from typing import List, Optional, Literal, Dict, Any

ScenarioName = Literal["baseline","stress","optimistic"]

class UploadResult(BaseModel):
    loaded: Dict[str, int]

class ForecastRequest(BaseModel):
    horizon_days: conint(ge=1, le=60) = 35
    scenario: ScenarioName = "baseline"

class ForecastPoint(BaseModel):
    date: date
    net_cash: float
    cash_balance: float

class ForecastResponse(BaseModel):
    forecast: List[ForecastPoint]
    metrics: Optional[Dict[str, float]] = None
    scenario: ScenarioName = "baseline"

class ScenarioRequest(BaseModel):
    horizon_days: conint(ge=1, le=60) = 35
    scenario: ScenarioName = "baseline"
    fx_shock: confloat(ge=-0.5, le=0.5) = 0.0
    delay_top_inflow_days: conint(ge=0, le=30) = 0
    delay_top_outflow_days: conint(ge=0, le=30) = 0
    shift_purchases_days: conint(ge=0, le=30) = 0

class ScenarioResponse(BaseModel):
    run_id: str
    scenario: ScenarioName
    forecast_scenario: List[ForecastPoint]
    min_cash: float
    metrics: Optional[Dict[str, float]] = None

class AdviceAction(BaseModel):
    title: str
    amount: Optional[float] = None
    rationale: Optional[str] = None

class AdviceRequest(BaseModel):
    baseline: ForecastResponse
    scenario: ScenarioResponse

class AdviceResponse(BaseModel):
    run_id: str
    advice_text: str
    actions: List[AdviceAction] = []
