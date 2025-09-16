from pydantic import BaseModel, Field, conint, ConfigDict
from typing import List, Dict, Any, Optional

class ForecastRequest(BaseModel):
    horizon_days: conint(ge=1, le=60) = 14

class ForecastPoint(BaseModel):
    date: str
    net_cash: float
    cash_balance: float

class ForecastResponse(BaseModel):
    forecast: List[ForecastPoint]
    metrics: Dict[str, float]

class ScenarioRequest(BaseModel):
    horizon_days: conint(ge=1, le=60) = 14
    fx_shock: float = 0.0                        # +0.1 = USD +10%
    delay_top_inflow_days: int = 0               # задержка крупнейшего поступления
    delay_top_outflow_days: int = 0              # задержка крупнейшей выплаты

class ScenarioResponse(BaseModel):
    forecast_scenario: List[ForecastPoint]
    min_cash: Optional[float] = None
    metrics: Dict[str, float]

class AdviceRequest(BaseModel):
    baseline: Dict[str, Any] = Field(..., description="Выход /forecast")
    scenario: Dict[str, Any] = Field(..., description="Выход /scenario")

class Action(BaseModel):
    title: str
    amount: Optional[float] = None
    rationale: Optional[str] = None

class AdviceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    advice_text: str
    actions: List[Action]
