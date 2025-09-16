from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload, forecast, scenario, advice, llm_test, dev_seed  # ⬅️ добавили

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
app.include_router(llm_test.router, prefix="/api")  # ⬅️ добавили
app.include_router(dev_seed.router, prefix="/api")

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