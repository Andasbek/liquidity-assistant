from fastapi import APIRouter
import pandas as pd, numpy as np
from datetime import date, timedelta
from ..utils.io import save_df
from ..services import etl

router = APIRouter(tags=["dev"])

@router.post("/dev/seed")
def dev_seed():
    # даты за ~60 дней
    start = date.today() - timedelta(days=60)
    dates = [start + timedelta(days=i) for i in range(61)]

    # fx
    np.random.seed(42)
    usd = 500 + np.cumsum(np.random.normal(0, 0.8, len(dates)))
    eur = 540 + np.cumsum(np.random.normal(0, 0.9, len(dates)))
    fx = pd.DataFrame({"date": dates, "USD/KZT": np.round(usd, 2), "EUR/KZT": np.round(eur, 2)})
    save_df("fx_rates.parquet", fx)

    # bank
    rows = []
    for d in dates:
        for _ in range(np.random.randint(0, 3)):
            ccy = np.random.choice(["KZT","USD"], p=[0.7,0.3])
            sign = np.random.choice([1,-1], p=[0.55,0.45])
            amt  = np.random.choice([200_000, 350_000, 800_000, 1_200_000])
            rows.append({"date": d, "account": "MAIN", "currency": ccy, "amount": float(sign*amt)})
    bank = pd.DataFrame(rows)
    save_df("bank_statements.parquet", bank)

    # payment calendar
    pc = []
    for d in dates[::7]:
        pc.append({"date": d, "type": "inflow", "currency": "KZT", "amount": 5_000_000, "memo": "invoice"})
    for d in dates[::14]:
        pc.append({"date": d, "type": "outflow", "currency": "KZT", "amount": 6_500_000, "memo": "payroll"})
    for d in dates[5::21]:
        pc.append({"date": d, "type": "outflow", "currency": "USD", "amount": 20_000, "memo": "import"})
    pay = pd.DataFrame(pc)
    # normalize как при загрузке
    from ..services import etl as _etl
    bank = _etl.normalize("bank_statements.csv", bank)
    pay  = _etl.normalize("payment_calendar.csv", pay)
    fx   = _etl.normalize("fx_rates.csv", fx)
    save_df("fx_rates.csv", fx)
    save_df("bank_statements.csv", bank)
    save_df("payment_calendar.csv", pay)

    # витрина
    daily = etl.build_daily_cashframe()
    save_df("daily_cash.parquet", daily)

    return {"ok": True, "rows": {
        "bank_statements.parquet": len(bank),
        "payment_calendar.parquet": len(pay),
        "fx_rates.parquet": len(fx),
        "daily_cash.parquet": len(daily),
    }}
