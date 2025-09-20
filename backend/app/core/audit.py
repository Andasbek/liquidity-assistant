import json, time
from datetime import datetime

def audit_log(action: str, request: dict, response: dict, user_id: str = "demo", role: str = "Analyst"):
    # для MVP: пишем в файл; для прод: в таблицу audit_log
    rec = {"ts": datetime.utcnow().isoformat(), "user": user_id, "role": role,
           "action": action, "request": request, "response": response}
    with open("/app/data/audit.log", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
