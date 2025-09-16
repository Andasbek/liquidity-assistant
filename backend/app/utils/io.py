from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _try_parquet_write(path: Path, df: pd.DataFrame) -> bool:
    try:
        df.to_parquet(path, index=False)  # требует pyarrow/fastparquet
        return True
    except Exception:
        return False

def _try_parquet_read(path: Path):
    try:
        return pd.read_parquet(path)
    except Exception:
        return None

def save_df(name: str, df: pd.DataFrame):
    path = DATA_DIR / name
    if name.endswith(".parquet"):
        if not _try_parquet_write(path, df):
            (path.with_suffix(".csv")).write_text("")  # создать файл, если нужно
            df.to_csv(path.with_suffix(".csv"), index=False)
    elif name.endswith(".csv"):
        df.to_csv(path, index=False)
    else:
        if not _try_parquet_write(path.with_suffix(".parquet"), df):
            df.to_csv(path.with_suffix(".csv"), index=False)

def load_df(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if name.endswith(".parquet"):
        if path.exists():
            df = _try_parquet_read(path); 
            if df is not None: return df
        csv_path = path.with_suffix(".csv")
        if csv_path.exists(): return pd.read_csv(csv_path)
        raise FileNotFoundError(str(path))
    elif name.endswith(".csv"):
        if not path.exists(): raise FileNotFoundError(str(path))
        return pd.read_csv(path)
    else:
        pq, csv = path.with_suffix(".parquet"), path.with_suffix(".csv")
        df = _try_parquet_read(pq) if pq.exists() else None
        if df is not None: return df
        if csv.exists(): return pd.read_csv(csv)
        raise FileNotFoundError(str(pq))

def path_exists(name: str) -> bool:
    p = DATA_DIR / name
    return p.exists() or (name.endswith(".parquet") and p.with_suffix(".csv").exists())
