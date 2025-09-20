# backend/app/routers/reports.py
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from ..core.auth import require_any
from ..models.schemas import AdviceRequest  # используем для валидации, но тело другое
from typing import Any, Dict, Optional
from ..services.reports import build_pdf

router = APIRouter(tags=["reports"])

@router.post("/report/pdf", dependencies=[Depends(require_any("CFO", "Treasurer", "Analyst"))])
def report_pdf(payload: Dict[str, Any]):
    """
    Ожидает тело вида:
    {
      "baseline": {...},     # ответ /forecast
      "scenario": {...},     # ответ /scenario
      "advice":   {...},     # ответ /advice
      "horizon_days": 14     # опционально
    }
    Возвращает application/pdf.
    """
    pdf = build_pdf(
        baseline=payload.get("baseline"),
        scenario=payload.get("scenario"),
        advice=payload.get("advice"),
        horizon_days=payload.get("horizon_days"),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="liquidity_brief.pdf"'},
    )
