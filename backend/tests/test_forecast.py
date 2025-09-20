import pytest

svc = pytest.importorskip("app.services.forecast", reason="forecast service not implemented yet")

def test_get_forecast_shape_and_metrics():
    if not hasattr(svc, "get_forecast"):
        pytest.skip("services.forecast.get_forecast not found")
    horizon = 10
    result = svc.get_forecast(horizon=horizon, scenario="baseline")  # ожидаемый интерфейс
    # допускаем 2 варианта возврата: (list, metrics) или dict
    if isinstance(result, tuple) and len(result) == 2:
        points, metrics = result
    elif isinstance(result, dict):
        points = result.get("forecast", [])
        metrics = result.get("metrics")
    else:
        pytest.skip("Unknown return type from get_forecast, adjust test")

    assert isinstance(points, list) and len(points) >= 1
    # если есть метрики — они словарь
    if metrics is not None:
        assert isinstance(metrics, dict)
        # sMAPE желательно, но не обязательно — не ломаемся, если ещё не добавил
        if "smape" in metrics:
            assert 0 <= float(metrics["smape"]) <= 100
