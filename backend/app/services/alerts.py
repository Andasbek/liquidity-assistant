from datetime import date, timedelta
from typing import List, Dict

def detect_cash_gap_14d(forecast_points: List[Dict]) -> List[Dict]:
    today = min(p["date"] for p in forecast_points)
    horizon = today + timedelta(days=14)
    return [p for p in forecast_points if today <= p["date"] <= horizon and p["cash_balance"] < 0]

def build_alerts(run_id: str, forecast_points: List[Dict]) -> List[Dict]:
    gaps = detect_cash_gap_14d(forecast_points)
    if not gaps:
        return []
    return [{
        "run_id": run_id,
        "dt": min(g["date"] for g in gaps),
        "kind": "cash_gap_14d",
        "payload": {"count": len(gaps)}
    }]
