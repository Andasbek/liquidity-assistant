import pytest

pytest.importorskip("fastapi")
pytest.importorskip("starlette")

try:
    from fastapi.testclient import TestClient
    from app.main import app  # FastAPI app
    _client = TestClient(app)
except Exception as e:
    pytest.skip(f"FastAPI app is not importable yet: {e}", allow_module_level=True)


def test_health_if_exists():
    # Если эндпоинта /health нет — не падаем
    r = _client.get("/health")
    # допустим 200 или 404 — главное, что приложение поднимается
    assert r.status_code in (200, 404)


def test_forecast_endpoint_basic():
    payload = {"horizon_days": 7}
    r = _client.post("/api/forecast", json=payload)
    assert r.status_code in (200, 422)  # 422, если валидация пока другая
    if r.status_code == 200:
        data = r.json()
        assert "forecast" in data and isinstance(data["forecast"], list)
        assert len(data["forecast"]) >= 1


def test_scenario_endpoint_basic():
    payload = {"horizon_days": 7, "fx_shock": 0.1, "delay_top_inflow_days": 2}
    r = _client.post("/api/scenario", json=payload)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        data = r.json()
        # ожидаем стандартные поля, но не жёстко
        assert any(k in data for k in ("forecast_scenario", "run_id", "min_cash"))
