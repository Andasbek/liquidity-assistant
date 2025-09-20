import json
import pandas as pd
from typing import Dict, Any, List, Tuple, Union
from . import llm
from datetime import date, datetime

SYSTEM_PROMPT = (
    "Ты финансовый аналитик (CFO brief writer). "
    "Пиши кратко и деловыми формулировками на русском. "
    "Структура ответа: 1) Итог; 2) Риски (даты/минимумы); 3) Рекомендации."
)

def make_advice(baseline: Dict[str, Any], scenario: Dict[str, Any], daily: pd.DataFrame) -> Tuple[str, List[Dict[str, Any]]]:
    actions: List[Dict[str, Any]] = []

    # --- Правила для действий ---
    min_cash = scenario.get("min_cash")
    if min_cash is None and not daily.empty:
        min_cash = float(daily["cash_balance"].min())

    deficit = 0.0
    if min_cash is not None and min_cash < 0:
        deficit = abs(min_cash) * 1.1  # 10% запас
        actions.append({
            "title": "Открыть краткосрочную кредитную линию",
            "amount": round(deficit, 2),
            "rationale": "Ожидается кассовый разрыв — требуется покрытие + подушка 10%."
        })

    bl_fc = baseline.get("forecast", [])
    last7 = bl_fc[-7:] if len(bl_fc) >= 7 else bl_fc
    if last7:
        avg_tail_balance = sum(p["cash_balance"] for p in last7) / len(last7)
        if avg_tail_balance > 10_000_000 and deficit == 0:
            actions.append({
                "title": "Разместить избыточную ликвидность на депозит",
                "amount": round(avg_tail_balance * 0.6, 2),
                "rationale": "Средний прогнозный остаток высок — можно безопасно разместить часть средств."
            })

    # --- Подготовка данных для LLM ---
    summary_payload = {
        "baseline_tail": last7,
        "scenario": {
            "min_cash": scenario.get("min_cash"),
            "metrics": scenario.get("metrics", {})
        },
        "actions": actions
    }
    user_prompt = (
    "Сформируй краткий бриф CFO по данным:\n"
    f"{json.dumps(summary_payload, ensure_ascii=False, indent=2, default=_json_default)}\n\n"
    "Не используй маркдаун-заголовки. Кратко, по делу, сохраняя числа."
    )

    # --- Вызов LLM (если настроен), иначе фоллбек ---
    try:
        text = llm.chat(SYSTEM_PROMPT, user_prompt)
    except Exception:
        text = ""

    if not text:
        # локальный фоллбек без LLM
        if actions:
            text = "Итог: есть потенциальные риски кассового разрыва. "
            text += f"Минимальный баланс: {round(min_cash,2) if min_cash is not None else 'N/A'}. "
            text += "Рекомендации: " + "; ".join([f"{a['title']} (~{a.get('amount','N/A')})" for a in actions])
        else:
            text = ("Итог: существенных рисков не выявлено. "
                    "Рекомендуется продолжать мониторинг курсов и графиков платежей, "
                    "поддерживая минимальный операционный остаток.")

    return text, actions

def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, pd.Timestamp):
        return o.to_pydatetime().isoformat()
    # на всякий случай — numpy/Decimal можно добросить сюда при необходимости
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

# мягкие импорты схем, чтобы не падать, если они чуть отличаются
try:
    from ..models.schemas import AdviceRequest, AdviceResponse, AdviceAction
except Exception:
    AdviceRequest = Dict  # type: ignore
    AdviceResponse = Dict  # type: ignore
    class AdviceAction(dict):  # type: ignore
        def __init__(self, title: str, amount: float | None = None, rationale: str | None = None):
            super().__init__(title=title, amount=amount, rationale=rationale)

def _points_to_df(points: List[Dict[str, Any]]) -> pd.DataFrame:
    """Преобразуем список точек в DataFrame с колонками date, net_cash, cash_balance."""
    if not points:
        return pd.DataFrame(columns=["date", "net_cash", "cash_balance"])
    df = pd.DataFrame(points)
    # приводим типы
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    for c in ("net_cash", "cash_balance"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["date", "net_cash", "cash_balance"]]

def build_advice(payload: Union[AdviceRequest, Dict[str, Any]]) -> Union[AdviceResponse, Dict[str, Any]]:
    """
    Обёртка под роутер /api/advice.
    Принимает payload с ключами baseline/scenario (как в твоём API),
    зовёт make_advice(...), пакует результат.
    """
    # к dict
    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload or {})
    baseline = data.get("baseline", {}) or {}
    scenario  = data.get("scenario", {}) or {}

    # достаём точки: baseline обычно "forecast", scenario — "forecast_scenario"
    base_pts = baseline.get("forecast") or baseline.get("forecast_scenario") or []
    scen_pts = scenario.get("forecast_scenario") or scenario.get("forecast") or []

    # daily — для правил (если надо брать min_cash из baseline/scenario — он уже у тебя вычисляется в сценарии)
    # Возьмём union, чтобы в daily была вся линия.
    daily = _points_to_df(base_pts if len(base_pts) >= len(scen_pts) else scen_pts)

    # вызываем твою логику
    advice_text, actions = make_advice(baseline, scenario, daily)

    # run_id лучше тащить из scenario, иначе дать дефолт
    run_id = scenario.get("run_id") or baseline.get("run_id") or "advice-run"

    # пробуем вернуть pydantic-модель (если совпадают поля)
    try:
        # Преобразуем actions к AdviceAction, если это простые dict
        norm_actions = []
        for a in actions:
            if isinstance(a, dict) and "title" in a:
                norm_actions.append(AdviceAction(
                    title=a.get("title"),
                    amount=a.get("amount"),
                    rationale=a.get("rationale"),
                ))
            else:
                norm_actions.append(a)
        return AdviceResponse(run_id=run_id, advice_text=advice_text, actions=norm_actions)
    except Exception:
        # fallback: обычный dict — FastAPI всё равно сериализует
        return {"run_id": run_id, "advice_text": advice_text, "actions": actions}