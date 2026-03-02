"""Shared test fixtures for Sanad AI backend tests."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for tests that don't need real DB."""
    with patch("backend.db.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def free_plan():
    """Free plan subscription response."""
    return {
        "subscription_id": None,
        "plan_tier": "free",
        "plan_name_ar": "مجاني",
        "plan_name_en": "Free",
        "limits": {
            "questions_per_day": 3,
            "questions_per_month": 30,
            "drafts_per_month": 1,
            "deadlines_per_month": 3,
            "contract_analyses_per_month": 3,
            "verdict_predictions_per_month": 2,
            "conversations": 5,
        },
        "features": {"model_modes": ["1.1"], "pdf_export": False},
        "status": "active",
        "billing_cycle": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
    }


@pytest.fixture
def pro_plan():
    """Pro plan subscription response."""
    return {
        "subscription_id": "sub-123",
        "plan_tier": "pro",
        "plan_name_ar": "احترافي",
        "plan_name_en": "Pro",
        "limits": {
            "questions_per_day": -1,
            "questions_per_month": -1,
            "drafts_per_month": -1,
            "deadlines_per_month": -1,
            "contract_analyses_per_month": -1,
            "verdict_predictions_per_month": -1,
            "conversations": -1,
        },
        "features": {"model_modes": ["1.1", "2.1"], "pdf_export": True},
        "status": "active",
        "billing_cycle": "monthly",
        "current_period_end": "2030-12-31T00:00:00+00:00",
        "cancel_at_period_end": False,
    }
