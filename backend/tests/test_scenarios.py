import pytest

svc = pytest.importorskip("app.services.scenarios", reason="scenarios service not implemented yet")

def test_run_scenario_contract():
    if not hasattr(svc, "run_scenario"):
        pytest.skip("services.scenarios.run_scenario not found")

    payload = dict(
        horizon_days=7,
        scenario="stress",
        fx_shock=0.1,
        delay_top_inflow_days=3,
        delay_top_outflow_days=0,
        shift_purchases_days=0,
    )
    res = svc.run_scenario(**payload)

    # допускаем 2 формы ответа: pydantic-модель с .model_dump() или dict
    if hasattr(res, "model_dump"):
        res = res.model_dump()

    assert isinstance(res, dict)
    assert "scenario" in res and res["scenario"] in ("baseline", "stress", "optimistic")
    assert "forecast_scenario" in res and isinstance(res["forecast_scenario"], list)
    assert "min_cash" in res
