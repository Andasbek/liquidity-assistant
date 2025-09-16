from fastapi import APIRouter, HTTPException
from ..models.schemas import AdviceRequest, AdviceResponse
from ..services import advisor
from ..utils.io import load_df

router = APIRouter(tags=["advice"])

@router.post("/advice", response_model=AdviceResponse)
def get_advice(req: AdviceRequest):
    # daily нужен для понимания текущего кэша и волатильности
    try:
        daily = load_df("daily_cash.parquet")
    except FileNotFoundError:
        raise HTTPException(400, detail="Upload data first via /upload")

    text, actions = advisor.make_advice(
        baseline=req.baseline, scenario=req.scenario, daily=daily
    )
    return AdviceResponse(advice_text=text, actions=actions)
