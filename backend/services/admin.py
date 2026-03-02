"""
Admin service for Sanad AI.
Handles admin-only operations: stats, user management, audit logging.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.db import get_supabase

log = logging.getLogger("sanad.admin")


async def check_admin(user_id: str) -> bool:
    """Check if user has admin role."""
    sb = get_supabase()
    if not sb:
        return False
    try:
        result = sb.rpc("is_admin", {"p_user_id": user_id}).execute()
        return bool(result.data)
    except Exception as e:
        log.error("Error checking admin status: %s", e)
        return False


async def get_user_role(user_id: str) -> str:
    """Get user's role (user/admin/super_admin)."""
    sb = get_supabase()
    if not sb:
        return "user"
    try:
        result = sb.rpc("get_user_role", {"p_user_id": user_id}).execute()
        return result.data or "user"
    except Exception as e:
        log.error("Error getting user role: %s", e)
        return "user"


async def get_admin_stats() -> dict:
    """Get dashboard statistics (admin only)."""
    sb = get_supabase()
    if not sb:
        return {}
    try:
        result = sb.rpc("get_admin_stats").execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
    except Exception as e:
        log.error("Error getting admin stats: %s", e)
    return {}


async def get_admin_users(limit: int = 50, offset: int = 0) -> list[dict]:
    """Get paginated user list with details (admin only)."""
    sb = get_supabase()
    if not sb:
        return []
    try:
        result = sb.rpc("get_admin_users", {
            "p_limit": limit,
            "p_offset": offset,
        }).execute()
        return result.data or []
    except Exception as e:
        log.error("Error getting admin users: %s", e)
        return []


async def log_admin_action(
    admin_user_id: str,
    action: str,
    target_user_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Record an admin action in the audit log."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("admin_audit_log").insert({
            "admin_user_id": admin_user_id,
            "action": action,
            "target_user_id": target_user_id,
            "details": details or {},
            "ip_address": ip_address,
        }).execute()
    except Exception as e:
        log.error("Error logging admin action: %s", e)


async def update_user_subscription_admin(
    admin_user_id: str,
    target_user_id: str,
    plan_tier: str,
) -> dict:
    """Admin: change a user's subscription plan."""
    sb = get_supabase()
    if not sb:
        return {"success": False, "error": "Database not available"}

    try:
        # Get the plan
        plan_result = sb.table("subscription_plans").select("id").eq("tier", plan_tier).execute()
        if not plan_result.data:
            return {"success": False, "error": f"Plan '{plan_tier}' not found"}
        plan_id = plan_result.data[0]["id"]

        # Deactivate existing subscription
        sb.table("user_subscriptions").update(
            {"status": "expired"}
        ).eq("user_id", target_user_id).eq("status", "active").execute()

        # Create new subscription
        sb.table("user_subscriptions").insert({
            "user_id": target_user_id,
            "plan_id": plan_id,
            "status": "active",
            "billing_cycle": "yearly",
            "current_period_end": "2099-12-31T00:00:00+00:00",
        }).execute()

        # Audit log
        await log_admin_action(
            admin_user_id=admin_user_id,
            action="change_plan",
            target_user_id=target_user_id,
            details={"new_plan": plan_tier},
        )

        # Invalidate subscription cache
        from backend.services.subscription import invalidate_subscription_cache
        invalidate_subscription_cache(target_user_id)

        return {"success": True, "plan_tier": plan_tier}
    except Exception as e:
        log.error("Error updating user subscription: %s", e)
        return {"success": False, "error": str(e)}
