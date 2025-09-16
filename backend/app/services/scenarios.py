import pandas as pd

def apply_scenarios(
    daily: pd.DataFrame,
    fx_shock: float = 0.0,
    delay_top_inflow_days: int = 0,
    delay_top_outflow_days: int = 0,
) -> pd.DataFrame:
    """
    Имитация:
      - fx_shock: глобально увеличивает положительные нетто-потоки (экспортная выручка) и/или уменьшает отрицательные? 
        В MVP применим коэффициент к net_cash > 0: net_cash *= (1 + fx_shock)
      - задержка крупнейшего inflow/outflow: сдвигает одну из дат нетто-потока
        В MVP: берём дни с экстремумом и переносим их сумму на d дней вперёд.
    """
    df = daily.copy().sort_values("date")
    df["date"] = pd.to_datetime(df["date"])
    # 1) FX shock — только к положительным днёвкам (упрощение)
    if fx_shock != 0:
        pos = df["net_cash"] > 0
        df.loc[pos, "net_cash"] = df.loc[pos, "net_cash"] * (1.0 + fx_shock)

    # 2) Перенос крупнейшего поступления / выплаты
    df = _delay_extreme(df, is_inflow=True, days=delay_top_inflow_days)
    df = _delay_extreme(df, is_inflow=False, days=delay_top_outflow_days)

    # Пересчёт баланса
    df = df.sort_values("date")
    df["cash_balance"] = df["net_cash"].cumsum()
    return df

def _delay_extreme(df: pd.DataFrame, is_inflow: bool, days: int) -> pd.DataFrame:
    if days == 0 or df.empty:
        return df
    df = df.copy()
    key_row = df.loc[df["net_cash"].idxmax()] if is_inflow else df.loc[df["net_cash"].idxmin()]
    idx = df.index[df["date"] == key_row["date"]][0]
    amount = key_row["net_cash"]

    # обнуляем исходный день и переносим на days вперёд
    df.at[idx, "net_cash"] = df.at[idx, "net_cash"] - amount
    new_date = pd.to_datetime(key_row["date"]) + pd.Timedelta(days=days)
    # вставка/агрегация на новую дату
    if new_date in pd.to_datetime(df["date"]).values:
        j = df.index[pd.to_datetime(df["date"]) == new_date][0]
        df.at[j, "net_cash"] = df.at[j, "net_cash"] + amount
    else:
        df = pd.concat([df, pd.DataFrame({"date": [new_date], "net_cash": [amount]})], ignore_index=True)
    return df
