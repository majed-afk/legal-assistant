"""Tests for backend.services.subscription — plan limits, trials, and usage checks."""
import pytest
from unittest.mock import AsyncMock, patch

from backend.services.subscription import (
    check_limit,
    check_model_mode,
    get_trial_status,
    _action_label,
    _free_plan_response,
    FREE_LIMITS,
    FREE_FEATURES,
    TRIAL_CONFIG,
)


# ---------------------------------------------------------------------------
# Helper: build mock subscription responses
# ---------------------------------------------------------------------------

def _make_free_sub():
    return {
        "subscription_id": None,
        "plan_tier": "free",
        "plan_name_ar": "مجاني",
        "plan_name_en": "Free",
        "limits": FREE_LIMITS,
        "features": FREE_FEATURES,
        "status": "active",
        "billing_cycle": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
    }


def _make_pro_sub():
    return {
        "subscription_id": "sub-abc",
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


# ===================================================================
# check_limit
# ===================================================================

class TestCheckLimit:
    """Tests for the check_limit function."""

    @pytest.mark.asyncio
    async def test_free_user_under_daily_limit_allowed(self):
        """Free user who has NOT reached the daily question limit should be allowed."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
            patch("backend.services.subscription.get_usage_today", new_callable=AsyncMock) as mock_daily,
            patch("backend.services.subscription.get_usage_monthly", new_callable=AsyncMock) as mock_monthly,
        ):
            mock_sub.return_value = _make_free_sub()
            mock_daily.return_value = {"questions_count": 1, "drafts_count": 0, "deadlines_count": 0}
            mock_monthly.return_value = {"questions": 1, "drafts": 0, "deadlines": 0}

            allowed, msg = await check_limit("user-1", "questions")

            assert allowed is True
            assert msg is None

    @pytest.mark.asyncio
    async def test_free_user_at_daily_limit_blocked(self):
        """Free user who has reached the daily question limit should be blocked."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
            patch("backend.services.subscription.get_usage_today", new_callable=AsyncMock) as mock_daily,
        ):
            mock_sub.return_value = _make_free_sub()
            # Daily limit for free = 3
            mock_daily.return_value = {"questions_count": 3, "drafts_count": 0, "deadlines_count": 0}

            allowed, msg = await check_limit("user-1", "questions")

            assert allowed is False
            assert msg is not None
            assert "اليومي" in msg
            assert "مجاني" in msg

    @pytest.mark.asyncio
    async def test_free_user_at_monthly_limit_blocked(self):
        """Free user who has reached the monthly draft limit should be blocked."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
            patch("backend.services.subscription.get_usage_monthly", new_callable=AsyncMock) as mock_monthly,
        ):
            mock_sub.return_value = _make_free_sub()
            # Monthly drafts limit for free = 1
            mock_monthly.return_value = {"questions": 0, "drafts": 1, "deadlines": 0}

            allowed, msg = await check_limit("user-1", "drafts")

            assert allowed is False
            assert msg is not None
            assert "الشهري" in msg

    @pytest.mark.asyncio
    async def test_pro_user_unlimited_always_allowed(self):
        """Pro user with -1 limits should always be allowed."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
        ):
            mock_sub.return_value = _make_pro_sub()

            for action in ["questions", "drafts", "deadlines", "contract_analyses", "verdict_predictions"]:
                allowed, msg = await check_limit("user-pro", action)
                assert allowed is True, f"Pro user blocked for action: {action}"
                assert msg is None

    @pytest.mark.asyncio
    async def test_unknown_action_type_allowed(self):
        """Unknown action types should be allowed (no mapping → pass through)."""
        allowed, msg = await check_limit("user-1", "unknown_action")
        assert allowed is True
        assert msg is None


# ===================================================================
# check_model_mode
# ===================================================================

class TestCheckModelMode:
    """Tests for the check_model_mode function."""

    @pytest.mark.asyncio
    async def test_free_user_mode_1_1_allowed(self):
        """Free user requesting mode 1.1 (included in free plan) should be allowed."""
        with patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub:
            mock_sub.return_value = _make_free_sub()

            allowed, msg = await check_model_mode("user-1", "1.1")

            assert allowed is True
            assert msg is None

    @pytest.mark.asyncio
    async def test_free_user_mode_2_1_with_trials_remaining(self):
        """Free user requesting mode 2.1 with trials remaining should be allowed."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
            patch("backend.services.subscription.get_trial_status", new_callable=AsyncMock) as mock_trial,
        ):
            mock_sub.return_value = _make_free_sub()
            mock_trial.return_value = {"used": 1, "max": 3, "remaining": 2}

            allowed, msg = await check_model_mode("user-1", "2.1")

            assert allowed is True
            assert msg is None

    @pytest.mark.asyncio
    async def test_free_user_mode_2_1_no_trials_blocked(self):
        """Free user requesting mode 2.1 with no trials remaining should be blocked."""
        with (
            patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub,
            patch("backend.services.subscription.get_trial_status", new_callable=AsyncMock) as mock_trial,
        ):
            mock_sub.return_value = _make_free_sub()
            mock_trial.return_value = {"used": 3, "max": 3, "remaining": 0}

            allowed, msg = await check_model_mode("user-1", "2.1")

            assert allowed is False
            assert msg is not None
            assert "التجارب المجانية" in msg
            assert "ترقَّ" in msg

    @pytest.mark.asyncio
    async def test_pro_user_mode_2_1_allowed(self):
        """Pro user requesting mode 2.1 (included in pro plan) should be allowed."""
        with patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub:
            mock_sub.return_value = _make_pro_sub()

            allowed, msg = await check_model_mode("user-pro", "2.1")

            assert allowed is True
            assert msg is None

    @pytest.mark.asyncio
    async def test_free_user_unknown_mode_blocked(self):
        """Free user requesting an unknown mode should be blocked."""
        with patch("backend.services.subscription.get_user_subscription", new_callable=AsyncMock) as mock_sub:
            mock_sub.return_value = _make_free_sub()

            allowed, msg = await check_model_mode("user-1", "3.0")

            assert allowed is False
            assert msg is not None
            assert "غير متاح" in msg


# ===================================================================
# get_trial_status
# ===================================================================

class TestGetTrialStatus:
    """Tests for the get_trial_status function."""

    @pytest.mark.asyncio
    async def test_returns_correct_remaining_from_db(self):
        """Trial status should reflect database values correctly."""
        with patch("backend.services.subscription.get_supabase") as mock_sb:
            mock_client = mock_sb.return_value
            mock_result = type("Result", (), {"data": [{"current_count": 2, "max_count": 3}]})()
            mock_client.rpc.return_value.execute.return_value = mock_result

            result = await get_trial_status("user-1", "model_mode_2.1")

            assert result["used"] == 2
            assert result["max"] == 3
            assert result["remaining"] == 1

    @pytest.mark.asyncio
    async def test_returns_full_quota_when_no_db(self):
        """When Supabase is unavailable, should return full trial quota."""
        with patch("backend.services.subscription.get_supabase") as mock_sb:
            mock_sb.return_value = None

            result = await get_trial_status("user-1", "model_mode_2.1")

            assert result["used"] == 0
            assert result["max"] == 3
            assert result["remaining"] == 3

    @pytest.mark.asyncio
    async def test_remaining_never_negative(self):
        """Remaining count should never be negative even if used > max."""
        with patch("backend.services.subscription.get_supabase") as mock_sb:
            mock_client = mock_sb.return_value
            mock_result = type("Result", (), {"data": [{"current_count": 5, "max_count": 3}]})()
            mock_client.rpc.return_value.execute.return_value = mock_result

            result = await get_trial_status("user-1", "model_mode_2.1")

            assert result["remaining"] == 0


# ===================================================================
# _action_label (helper)
# ===================================================================

class TestActionLabel:
    """Tests for the _action_label helper."""

    def test_known_labels_return_arabic(self):
        assert _action_label("questions") == "سؤال"
        assert _action_label("drafts") == "مذكرة"
        assert _action_label("deadlines") == "حساب مهلة"
        assert _action_label("contract_analyses") == "تحليل عقد"
        assert _action_label("verdict_predictions") == "توقع حكم"

    def test_unknown_label_returns_input(self):
        assert _action_label("some_unknown") == "some_unknown"


# ===================================================================
# _free_plan_response (helper)
# ===================================================================

class TestFreePlanResponse:
    """Tests for the _free_plan_response helper."""

    def test_structure_is_correct(self):
        resp = _free_plan_response()
        assert resp["subscription_id"] is None
        assert resp["plan_tier"] == "free"
        assert resp["plan_name_ar"] == "مجاني"
        assert resp["plan_name_en"] == "Free"
        assert resp["status"] == "active"
        assert resp["billing_cycle"] is None
        assert resp["current_period_end"] is None
        assert resp["cancel_at_period_end"] is False

    def test_limits_match_free_limits(self):
        resp = _free_plan_response()
        assert resp["limits"] == FREE_LIMITS

    def test_features_match_free_features(self):
        resp = _free_plan_response()
        assert resp["features"] == FREE_FEATURES
        assert "1.1" in resp["features"]["model_modes"]
        assert resp["features"]["pdf_export"] is False

    def test_free_limits_values(self):
        """Verify specific free plan limit values."""
        assert FREE_LIMITS["questions_per_day"] == 3
        assert FREE_LIMITS["questions_per_month"] == 30
        assert FREE_LIMITS["drafts_per_month"] == 1
        assert FREE_LIMITS["deadlines_per_month"] == 3
        assert FREE_LIMITS["conversations"] == 5

    def test_trial_config_exists(self):
        """Verify trial configuration is properly set."""
        assert "model_mode_2.1" in TRIAL_CONFIG
        assert TRIAL_CONFIG["model_mode_2.1"]["max_allowed"] == 3
