import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from . import llm

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
        f"{json.dumps(summary_payload, ensure_ascii=False, indent=2)}\n\n"
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
