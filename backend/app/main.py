from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload, forecast, scenario, advice, llm_test, dev_seed, sources, reports, backtest

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

scheduler = None

app = FastAPI(title="Liquidity Assistant API", version="0.1.0", description="...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(scenario.router, prefix="/api")
app.include_router(advice.router, prefix="/api")
app.include_router(llm_test.router, prefix="/api")
app.include_router(dev_seed.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/llm/test-inline")
def llm_test_inline():
    try:
        from .services import llm
        from .core import config
        sample = llm.chat("Ты ассистент.", "Ответь одним словом: Готово.")
        base_url = config.OLLAMA_BASE_URL if config.LLM_PROVIDER == "ollama" else config.OPENAI_BASE_URL
        return {"ok": True, "provider": config.LLM_PROVIDER, "model": config.LLM_MODEL, "base_url": base_url, "sample": sample}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    
def _scheduled_sync():
    from .routers.sources import sources_sync  # локальный импорт, чтобы избежать циклов
    try:
        res = sources_sync(fx=True, bank=True, calendar=True, days=60)
        print(f"[{datetime.now().isoformat()}] scheduled sync ok -> {res['loaded']}")
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] scheduled sync failed: {e}")

@app.on_event("startup")
def _startup():
    from .core import config
    global scheduler
    if config.SYNC_EVERY_MIN and config.SYNC_EVERY_MIN > 0:
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(_scheduled_sync, "interval", minutes=config.SYNC_EVERY_MIN, id="sync_job", max_instances=1)
        scheduler.start()
        print(f"APScheduler started: every {config.SYNC_EVERY_MIN} min")
    else:
        print("APScheduler disabled (SYNC_EVERY_MIN=0)")

@app.on_event("shutdown")
def _shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown()