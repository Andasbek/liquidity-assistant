import pytest
import pandas as pd
from datetime import date

# мягкие импорты — если модуль ещё не добавлен, тесты скипнутся
su = pytest.importorskip("app.services.scenarios_utils", reason="scenarios_utils not implemented")
scen = pytest.importorskip("app.services.scenarios", reason="scenarios service not implemented")


def _make_daily():
    # базовый трёхдневный ряд
    return pd.DataFrame({
        "date": [date(2025, 9, 1), date(2025, 9, 2), date(2025, 9, 3)],
        "net_cash": [200_000.0, -50_000.0, 80_000.0],
        "cash_balance": [200_000.0, 150_000.0, 230_000.0],  # для B0 восстановления
    })


def test_fx_shock_only_positive_scaled():
    daily = _make_daily()
    out = su.apply_scenarios_safe(daily, base_balance0=0.0, fx_shock=0.1)
    # положительные дни увеличились на 10%
    assert out.loc[out["date"] == pd.to_datetime(date(2025, 9, 1)), "net_cash"].iloc[0] == pytest.approx(220_000.0)
    assert out.loc[out["date"] == pd.to_datetime(date(2025, 9, 3)), "net_cash"].iloc[0] == pytest.approx(88_000.0)
    # отрицательный день остался прежним
    assert out.loc[out["date"] == pd.to_datetime(date(2025, 9, 2)), "net_cash"].iloc[0] == pytest.approx(-50_000.0)


def test_delay_extreme_inflow_preserves_sum_and_shifts_date():
    daily = _make_daily()
    total_before = daily["net_cash"].sum()
    out = su.apply_scenarios_safe(daily, base_balance0=0.0, delay_top_inflow_days=2)

    total_after = out["net_cash"].sum()
    assert total_after == pytest.approx(total_before)  # сумма сохранена

    # крупнейший inflow был на 2025-09-01 -> должен появиться на 2025-09-03
    dst = pd.to_datetime(date(2025, 9, 3))
    assert dst in set(out["date"])

    # исходный день 2025-09-01 теперь должен быть без той суммы (стал меньше)
    src_val_after = out.loc[out["date"] == pd.to_datetime(date(2025, 9, 1)), "net_cash"].iloc[0]
    assert src_val_after <= 0.0 or src_val_after < 200_000.0


def test_balance_recomputed_from_b0():
    daily = _make_daily()
    # восстановим B0 из baseline: B0 = B_first - net_first = 0
    out = su.apply_scenarios_safe(daily, base_balance0=0.0, fx_shock=0.1)
    # проверим первый день: 0 + 220_000 = 220_000
    first_row = out.sort_values("date").iloc[0]
    assert first_row["cash_balance"] == pytest.approx(220_000.0)
    # кумулятивно второй день: 220_000 + (-50_000) = 170_000
    second_row = out.sort_values("date").iloc[1]
    assert second_row["cash_balance"] == pytest.approx(170_000.0)


def test_run_scenario_smoke():
    # не проверяем точные числа — только контракт и ключевые поля
    res = scen.run_scenario(horizon_days=7, scenario="baseline", fx_shock=0.05, delay_top_inflow_days=1)
    assert isinstance(res, dict)
    assert "run_id" in res and "scenario" in res and "forecast_scenario" in res and "min_cash" in res
    assert isinstance(res["forecast_scenario"], list)
    # последовательность точек должна быть не пустой
    assert len(res["forecast_scenario"]) >= 1

def test_delay_extreme_outflow_shifts_min_date():
    daily = _make_daily()
    # добавим сильный outflow на 2025-09-02 для явного экстремума
    daily.loc[1, "net_cash"] = -300_000.0
    out = su.apply_scenarios_safe(daily, base_balance0=0.0, delay_top_outflow_days=2)

    # outflow -300k должен «уехать» на 2025-09-04
    assert pd.to_datetime(date(2025, 9, 4)) in set(out["date"])
