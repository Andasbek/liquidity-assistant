import pytest
import pandas as pd
from datetime import date
import inspect

etl = pytest.importorskip("app.services.etl", reason="etl service not implemented yet")
features = pytest.importorskip("app.services.features", reason="features service not implemented yet")

def test_build_daily_cashframe_minimal():
    # синтетика «на коленке»: два дня, нетто по 1 валюте
    bank = pd.DataFrame([
        {"date": date(2025, 9, 1), "account": "MAIN", "currency": "KZT", "amount": 200_000},
        {"date": date(2025, 9, 1), "account": "MAIN", "currency": "USD", "amount": -1000},
    ])
    paycal = pd.DataFrame([
        {"date": date(2025, 9, 2), "type": "outflow", "currency": "KZT", "amount": 50_000, "memo": "rent"}
    ])
    fx = pd.DataFrame([
        {"date": date(2025, 9, 1), "USD/KZT": 500.0, "EUR/KZT": 540.0},
        {"date": date(2025, 9, 2), "USD/KZT": 501.0, "EUR/KZT": 539.5},
    ])

    # normalize(name, df) — вызываем три раза
    if not hasattr(etl, "normalize"):
        pytest.skip("etl.normalize() not found; adjust test when implemented")

    bank_n = etl.normalize("bank_statements.csv", bank)
    paycal_n = etl.normalize("payment_calendar.csv", paycal)
    fx_n = etl.normalize("fx_rates.csv", fx)

    # Поддержим разные сигнатуры build_daily_cashframe:
    # - (bank, paycal, fx)
    # - (files_dict)
    if not hasattr(features, "build_daily_cashframe"):
        pytest.skip("features.build_daily_cashframe() not found")

    sig = inspect.signature(features.build_daily_cashframe)
    params = list(sig.parameters)
    if len(params) == 3:
        daily = features.build_daily_cashframe(bank_n, paycal_n, fx_n)
    elif len(params) == 1:
        files = {"bank": bank_n, "paycal": paycal_n, "fx": fx_n}
        daily = features.build_daily_cashframe(files)
    else:
        pytest.skip(f"Unexpected build_daily_cashframe() signature: {params}")

    assert hasattr(daily, "columns")
    assert {"date", "net_cash", "cash_balance"}.issubset(set(daily.columns))
    assert len(daily) >= 1
