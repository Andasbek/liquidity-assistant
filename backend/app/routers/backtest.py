# backend/app/routers/backtest.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..core.auth import require_any
from ..services.backtest import BacktestParams, rolling_backtest

router = APIRouter(tags=["backtest"])

class BacktestRequest(BaseModel):
    horizon: int = Field(7, ge=1, le=60)
    window: int = Field(30, ge=7)
    step: int = Field(1, ge=1)
    target_col: str = "net_cash"
    models: Optional[List[str]] = None  # ["naive_last","naive_mean","arima","prophet"]

@router.post("/backtest", dependencies=[Depends(require_any("Analyst","Treasurer","CFO"))])
def run_backtest(req: BacktestRequest) -> Dict[str, Any]:
    params = BacktestParams(
        horizon=req.horizon, window=req.window, step=req.step,
        target_col=req.target_col, use_models=req.models
    )
    res = rolling_backtest(params)
    # конвертируем DataFrame → JSON-сериализуемый формат
    summary = res["summary"].to_dict(orient="records")
    per_model = {
        m: df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
        for m, df in res["per_model"].items()
    }
    return {
        "summary": summary,
        "per_model": per_model,
        "params": res["params"],
    }
