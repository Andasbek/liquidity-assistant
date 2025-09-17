from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
import pandas as pd
from ..sources.fx_api import fetch_fx_rates, FX_PAIRS_DEFAULT
from ..sources.bank_mock import pull_bank_statements, pull_payment_calendar
from ..services import etl
from ..utils.io import save_df

router = APIRouter(tags=["sources"])

@router.post("/sources/sync")
def sources_sync(
    fx: bool = Query(True),
    bank: bool = Query(True),
    calendar: bool = Query(True),
    days: int = Query(60, ge=7, le=365),
):
    """
    Подтягивает данные из источников (моки) за последние N дней,
    сохраняет в processed, пересобирает витрину и возвращает размеры.
    """
    end = date.today()
    start = end - timedelta(days=days)
    loaded = {}

    if fx:
        df_fx = fetch_fx_rates(start, end, pairs=FX_PAIRS_DEFAULT)
        save_df("fx_rates.parquet", df_fx)
        loaded["fx_rates"] = int(len(df_fx))

    if bank:
        df_bank = pull_bank_statements(start, end)
        save_df("bank_statements.parquet", df_bank)
        loaded["bank_statements"] = int(len(df_bank))

    if calendar:
        df_cal = pull_payment_calendar(start, end)
        save_df("payment_calendar.parquet", df_cal)
        loaded["payment_calendar"] = int(len(df_cal))

    try:
        daily = etl.build_daily_cashframe()
        save_df("daily_cash.parquet", daily)
        loaded["daily_cash"] = int(len(daily))
    except Exception as e:
        raise HTTPException(400, detail=f"ETL failed after sync: {e}")

    return {"ok": True, "loaded": loaded, "range": {"start": start.isoformat(), "end": end.isoformat()}}
