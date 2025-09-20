# backend/tests/test_forecast_df_truthiness.py
import pytest, pandas as pd
svc = pytest.importorskip("app.services.forecast")
def test_forecast_accepts_none_or_df():
    pts, m = svc.forecast_cash(pd.DataFrame(columns=["date","net_cash","cash_balance"]), 3)
    assert isinstance(pts, list)
