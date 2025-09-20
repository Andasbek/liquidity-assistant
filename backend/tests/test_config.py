# backend/tests/test_config.py
from app.core import config


def test_llm_config():
    assert config.LLM_PROVIDER in ("ollama", "openai", "")
    assert isinstance(config.LLM_MODEL, str)
    assert isinstance(config.LLM_TIMEOUT, int)


def test_database_url():
    assert config.DATABASE_URL.startswith("postgresql://")


def test_forecast_params():
    assert config.DEFAULT_HORIZON_DAYS > 0
    assert config.REPORT_TIMEOUT_S > 0
    assert config.SCENARIO_TIMEOUT_S > 0
    assert config.ALERT_WINDOW_DAYS > 0


def test_kpi_targets():
    assert 0 < config.KPI_MAPE_TARGET <= 100
    assert 0 <= config.KPI_PRECISION_GAP_TARGET <= 1


def test_fx_pairs():
    assert isinstance(config.FX_PAIRS, list)
    for pair in config.FX_PAIRS:
        assert "/" in pair


def test_security_settings():
    assert isinstance(config.JWT_SECRET, str)
    assert isinstance(config.JWT_ISSUER, str)
    assert isinstance(config.JWT_AUDIENCE, str)
    assert isinstance(config.DEFAULT_ROLE, str)


def test_logging_settings():
    assert config.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    assert config.LOG_FORMAT in ("json", "text")


def test_misc_settings():
    assert isinstance(config.TIMEZONE, str)
    assert isinstance(config.BASE_CURRENCY, str)
