import pandas as pd

def ensure_non_empty(df: pd.DataFrame, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} is empty")
