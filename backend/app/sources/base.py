from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class Source(ABC):
    name: str

    @abstractmethod
    def pull(self, start: date, end: date) -> pd.DataFrame:
        ...

def ensure_date_cols(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
