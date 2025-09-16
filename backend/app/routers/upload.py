from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
import pandas as pd
from pandas.errors import ParserError
from pathlib import Path

from ..services import etl
from ..utils.io import save_df

router = APIRouter(tags=["upload"])

REQUIRED_FILES = {"bank_statements.csv", "payment_calendar.csv", "fx_rates.csv"}

def _friendly_schema_hint(name: str) -> str:
    if name == "bank_statements.csv":
        return "Ожидаются колонки: date, account, currency, amount (inflow +, outflow -)"
    if name == "payment_calendar.csv":
        return "Ожидаются колонки: date, type(inflow|outflow), currency, amount[, memo]"
    if name == "fx_rates.csv":
        return "Ожидаются колонки: date, USD/KZT, EUR/KZT, ..."
    return "Проверьте схему файла."

@router.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    """
    Принимает строго 3 CSV:
      - bank_statements.csv
      - payment_calendar.csv
      - fx_rates.csv
    Сохраняет их как parquet, затем строит витрину daily_cash.parquet.
    Возвращает размеры загруженных датасетов и витрины.
    """
    # 1) Проверим состав файлов
    raw_names = [f.filename for f in files]
    # сравниваем по basename, а не по полному пути
    names = [Path(n).name for n in raw_names]
    missing = REQUIRED_FILES - set(names)
    extra = set(names) - REQUIRED_FILES
    if missing:
        raise HTTPException(400, detail=f"Не хватает файлов: {sorted(missing)}. Должны быть: {sorted(REQUIRED_FILES)}")
    if extra:
        raise HTTPException(400, detail=f"Лишние файлы: {sorted(extra)}. Разрешены только: {sorted(REQUIRED_FILES)}")

    # 2) Считываем каждый CSV с явными сообщениями об ошибках
    loaded: Dict[str, int] = {}
    for f in files:
        try:
            # Принудительно укажем UTF-8 и обработаем разделитель
            df = pd.read_csv(f.file, encoding="utf-8", sep=",")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(f.file, encoding="cp1251", sep=",")
            except Exception as e:
                raise HTTPException(
                    400,
                    detail=f"{f.filename}: ошибка кодировки (UTF-8/CP1251 не подошли): {e}"
                )
        except ParserError as e:
            raise HTTPException(
                400,
                detail=f"{f.filename}: ошибка парсинга CSV (возможно, неверный разделитель/кавычки). {e}"
            )
        except Exception as e:
            raise HTTPException(400, detail=f"{f.filename}: не удалось прочитать файл: {e}")

        # Нормализация по типу файла
        try:
            df = etl.normalize(f.filename, df)
        except Exception as e:
            raise HTTPException(
                400,
                detail=f"{f.filename}: схема/данные не прошли нормализацию: {e}. "
                       f"{_friendly_schema_hint(f.filename)}"
            )

        # Сохранение в parquet (в /data/processed)
        try:
            save_df(f.filename.replace(".csv", ".parquet"), df)
            loaded[f.filename] = int(len(df))
        except Exception as e:
            raise HTTPException(400, detail=f"{f.filename}: не удалось сохранить parquet: {e}")

    # 3) ETL витрины
    try:
        daily = etl.build_daily_cashframe()
        save_df("daily_cash.parquet", daily)
        loaded["daily_cash.parquet"] = int(len(daily))
    except FileNotFoundError as e:
        raise HTTPException(400, detail=f"ETL failed: отсутствуют источники — {e}")
    except Exception as e:
        raise HTTPException(400, detail=f"ETL failed: {e}")

    return {"loaded": loaded}
