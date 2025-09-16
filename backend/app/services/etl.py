import pandas as pd
import numpy as np
from ..utils.io import load_df, path_exists

def normalize(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Приводим CSV к ожидаемым схемам, лёгкая очистка."""
    if name == "bank_statements.csv":
        # ожидаем: date, account, currency, amount (inflows +, outflows -)
        cols = {c.lower(): c for c in df.columns}
        df.rename(columns={k: k.lower() for k in df.columns}, inplace=True)
        need = {"date", "account", "currency", "amount"}
        if not need.issubset(set(df.columns)):
            raise ValueError(f"bank_statements.csv must have: {sorted(need)}")
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        return df

    if name == "payment_calendar.csv":
        # ожидаем: date, type[inflow|outflow], currency, amount, memo
        df.rename(columns={k: k.lower() for k in df.columns}, inplace=True)
        need = {"date", "type", "currency", "amount"}
        if not need.issubset(set(df.columns)):
            raise ValueError(f"payment_calendar.csv must have: {sorted(need)}")
        df["date"] = pd.to_datetime(df["date"]).dt.date
        sign = df["type"].str.lower().map({"inflow": 1, "outflow": -1}).fillna(0)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0) * sign
        return df

    if name == "fx_rates.csv":
        # ожидаем: date, USD/KZT, EUR/KZT ...
        df.rename(columns={k: k.upper() if k != "date" else k for k in df.columns}, inplace=True)
        if "date" not in df.columns:
            raise ValueError("fx_rates.csv must have 'date' column")
        df["date"] = pd.to_datetime(df["date"]).dt.date
        for c in df.columns:
            if c == "date": continue
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    raise ValueError(f"Unknown file: {name}")

def build_daily_cashframe() -> pd.DataFrame:
    """
    Собирает дневные нетто-потоки и кумулятивный баланс кэша в базовой валюте (KZT).
    Ожидаемые источники (parquet/csv):
      - bank_statements.*:  date, account, currency, amount  (inflow +, outflow -)
      - payment_calendar.*: date, type(inflow|outflow), currency, amount[, memo]
      - fx_rates.*:         date, USD/KZT, EUR/KZT, ...
    Возвращает DataFrame: [date, net_cash, cash_balance]
    """
    # 1) Проверяем наличие исходников (parquet или csv — path_exists учитывает оба)
    if not (path_exists("bank_statements.parquet")
            and path_exists("payment_calendar.parquet")
            and path_exists("fx_rates.parquet")):
        raise FileNotFoundError("Missing required sources: bank_statements, payment_calendar, fx_rates")

    # 2) Читаем данные (load_df сам попробует parquet, затем csv)
    bank = load_df("bank_statements.parquet").copy()
    pay  = load_df("payment_calendar.parquet").copy()
    fx   = load_df("fx_rates.parquet").copy()

    # 3) Мини-валидация и приведение типов
    for df in (bank, pay):
        df.columns = [c.lower() for c in df.columns]
        if not {"date", "currency", "amount"}.issubset(df.columns):
            raise ValueError("bank/payment must have columns: date, currency, amount")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["currency"] = df["currency"].astype(str).str.upper()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # 4) Объединяем операции
    ops = pd.concat([bank[["date", "currency", "amount"]],
                     pay[["date", "currency", "amount"]]], ignore_index=True)
    if ops.empty:
        return pd.DataFrame(columns=["date", "net_cash", "cash_balance"])

    # 5) Готовим курсы в long-вид
    if "date" not in fx.columns:
        raise ValueError("fx_rates must have 'date' column")
    fx["date"] = pd.to_datetime(fx["date"], errors="coerce")
    fx_cols = [c for c in fx.columns if c != "date"]
    if not fx_cols:
        raise ValueError("fx_rates must contain FX pair columns like 'USD/KZT'")

    fx_long = fx.melt(id_vars="date", var_name="pair", value_name="rate").dropna(subset=["rate"])
    fx_long["ccy"] = fx_long["pair"].astype(str).str.split("/").str[0].str.upper()
    fx_long = fx_long.sort_values(["ccy", "date"])
    fx_long["rate"] = fx_long.groupby("ccy")["rate"].ffill().bfill()

    # 6) Джоин курсов
    merged = ops.merge(
        fx_long[["date", "ccy", "rate"]],
        left_on=["date", "currency"], right_on=["date", "ccy"], how="left"
    ).drop(columns=["ccy"])
    # KZT = 1.0, остальным — найденный курс (с доп. ffill по дате)
    merged = merged.sort_values("date")
    merged["rate"] = np.where(merged["currency"].eq("KZT"), 1.0, merged["rate"])
    merged["rate"] = pd.Series(merged["rate"]).ffill().fillna(1.0).astype(float)

    # 7) Пересчёт в KZT
    merged["amount_kzt"] = np.where(
        merged["currency"].eq("KZT"),
        merged["amount"],
        merged["amount"] * merged["rate"]
    )

    # 8) Агрегат по дням
    daily = (merged.groupby("date", as_index=False)["amount_kzt"]
             .sum().rename(columns={"amount_kzt": "net_cash"}).sort_values("date"))

    # 9) Непрерывная шкала дат (правильный set_index → reindex)
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"])
        full_idx = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
        daily = (daily.set_index("date")
                       .reindex(full_idx)
                       .rename_axis("date")
                       .reset_index())
        daily["net_cash"] = daily["net_cash"].fillna(0.0)
        daily["date"] = daily["date"].dt.date  # теперь .dt работает, т.к. это Series datetime

    # 10) Кумулятивный баланс
    daily["cash_balance"] = daily["net_cash"].cumsum().astype(float)

    return daily[["date", "net_cash", "cash_balance"]]