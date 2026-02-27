"""
Subscription management service.
Handles plan lookups, usage tracking, and limit checking.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from backend.db import get_supabase


# ---- Default free plan limits (fallback if DB unavailable) ----
FREE_LIMITS = {
    "questions_per_day": 3,
    "questions_per_month": 30,
    "drafts_per_month": 1,
    "deadlines_per_month": 3,
    "conversations": 5,
}

FREE_FEATURES = {
    "model_modes": ["1.1"],
    "pdf_export": False,
}

# Map action types to usage field names and limit keys
ACTION_MAP = {
    "questions": {"field": "questions_count", "daily_key": "questions_per_day", "monthly_key": "questions_per_month"},
    "drafts": {"field": "drafts_count", "daily_key": None, "monthly_key": "drafts_per_month"},
    "deadlines": {"field": "deadlines_count", "daily_key": None, "monthly_key": "deadlines_per_month"},
}


async def get_user_subscription(user_id: str) -> dict:
    """
    Get user's active subscription with plan details.
    Returns free plan if no active subscription found.
    """
    sb = get_supabase()
    if not sb:
        return _free_plan_response()

    try:
        result = sb.rpc("get_user_subscription", {"p_user_id": user_id}).execute()
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return {
                "subscription_id": row["subscription_id"],
                "plan_tier": row["plan_tier"],
                "plan_name_ar": row["plan_name_ar"],
                "plan_name_en": row["plan_name_en"],
                "limits": row["plan_limits"],
                "features": row["plan_features"],
                "status": row["sub_status"],
                "billing_cycle": row["billing_cycle"],
                "current_period_end": row["current_period_end"],
                "cancel_at_period_end": row["cancel_at_period_end"],
            }
    except Exception as e:
        print(f"Error fetching subscription: {e}")

    return _free_plan_response()


async def get_all_plans() -> list[dict]:
    """Get all active subscription plans."""
    sb = get_supabase()
    if not sb:
        return []

    try:
        result = (
            sb.table("subscription_plans")
            .select("*")
            .eq("is_active", True)
            .order("price_monthly_sar")
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"Error fetching plans: {e}")
        return []


async def get_usage_today(user_id: str) -> dict:
    """Get user's usage for today."""
    sb = get_supabase()
    if not sb:
        return {"questions_count": 0, "drafts_count": 0, "deadlines_count": 0}

    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = (
            sb.table("usage_tracking")
            .select("questions_count, drafts_count, deadlines_count")
            .eq("user_id", user_id)
            .eq("date", today)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
    except Exception as e:
        print(f"Error fetching daily usage: {e}")

    return {"questions_count": 0, "drafts_count": 0, "deadlines_count": 0}


async def get_usage_monthly(user_id: str) -> dict:
    """Get user's usage for the current month."""
    sb = get_supabase()
    if not sb:
        return {"questions": 0, "drafts": 0, "deadlines": 0}

    try:
        result = sb.rpc("get_monthly_usage", {"p_user_id": user_id}).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
    except Exception as e:
        print(f"Error fetching monthly usage: {e}")

    return {"questions": 0, "drafts": 0, "deadlines": 0}


async def check_limit(user_id: str, action_type: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user can perform the given action.
    Returns (allowed, error_message).
    -1 in limits means unlimited.
    """
    if action_type not in ACTION_MAP:
        return True, None  # Unknown action — allow

    mapping = ACTION_MAP[action_type]
    sub = await get_user_subscription(user_id)
    limits = sub.get("limits", FREE_LIMITS)

    # Check daily limit (only for questions)
    daily_key = mapping["daily_key"]
    if daily_key:
        daily_limit = limits.get(daily_key, -1)
        if daily_limit != -1:
            usage_today = await get_usage_today(user_id)
            current = usage_today.get(mapping["field"], 0)
            if current >= daily_limit:
                plan_name = sub.get("plan_name_ar", "مجاني")
                return False, (
                    f"وصلت للحد اليومي ({daily_limit} {_action_label(action_type)}/يوم) "
                    f"في باقة {plan_name}. "
                    f"ترقَّ لباقة أعلى لزيادة الحد."
                )

    # Check monthly limit
    monthly_key = mapping["monthly_key"]
    if monthly_key:
        monthly_limit = limits.get(monthly_key, -1)
        if monthly_limit != -1:
            usage_monthly = await get_usage_monthly(user_id)
            # Map action type to monthly usage field name
            monthly_field = action_type  # "questions", "drafts", "deadlines"
            current = usage_monthly.get(monthly_field, 0)
            if current >= monthly_limit:
                plan_name = sub.get("plan_name_ar", "مجاني")
                return False, (
                    f"وصلت للحد الشهري ({monthly_limit} {_action_label(action_type)}/شهر) "
                    f"في باقة {plan_name}. "
                    f"ترقَّ لباقة أعلى لزيادة الحد."
                )

    return True, None


async def check_model_mode(user_id: str, model_mode: str) -> Tuple[bool, Optional[str]]:
    """Check if user's plan allows the requested model mode."""
    sub = await get_user_subscription(user_id)
    features = sub.get("features", FREE_FEATURES)
    allowed_modes = features.get("model_modes", ["1.1"])

    if model_mode not in allowed_modes:
        plan_name = sub.get("plan_name_ar", "مجاني")
        return False, (
            f"وضع الإجابة {model_mode} غير متاح في باقة {plan_name}. "
            f"ترقَّ للباقة الأساسية أو أعلى لاستخدام الوضع المفصّل."
        )

    return True, None


async def increment_usage(user_id: str, action_type: str) -> int:
    """
    Increment usage counter for the given action.
    Returns the new count after increment.
    """
    if action_type not in ACTION_MAP:
        return 0

    field = ACTION_MAP[action_type]["field"]
    sb = get_supabase()
    if not sb:
        return 0

    try:
        result = sb.rpc("increment_usage", {
            "p_user_id": user_id,
            "p_field": field,
        }).execute()
        return result.data if result.data else 0
    except Exception as e:
        print(f"Error incrementing usage: {e}")
        return 0


async def get_user_usage_summary(user_id: str) -> dict:
    """Get complete usage summary for user dashboard."""
    sub = await get_user_subscription(user_id)
    today = await get_usage_today(user_id)
    monthly = await get_usage_monthly(user_id)
    limits = sub.get("limits", FREE_LIMITS)

    return {
        "plan": {
            "tier": sub.get("plan_tier", "free"),
            "name_ar": sub.get("plan_name_ar", "مجاني"),
            "name_en": sub.get("plan_name_en", "Free"),
        },
        "today": today,
        "monthly": monthly,
        "limits": limits,
        "features": sub.get("features", FREE_FEATURES),
    }


# ---- Helpers ----

def _free_plan_response() -> dict:
    """Build a response dict for the free plan."""
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


def _action_label(action_type: str) -> str:
    """Arabic label for action type."""
    labels = {
        "questions": "سؤال",
        "drafts": "مذكرة",
        "deadlines": "حساب مهلة",
    }
    return labels.get(action_type, action_type)
