"""
Moyasar payment gateway integration.
Handles payment creation, verification, and webhook processing.

Moyasar API docs: https://moyasar.com/docs/api/
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from backend.config import MOYASAR_SECRET_KEY, MOYASAR_CALLBACK_URL
from backend.db import get_supabase


MOYASAR_API_BASE = "https://api.moyasar.com/v1"


def _moyasar_auth_header() -> dict:
    """Build Basic Auth header for Moyasar API."""
    credentials = base64.b64encode(f"{MOYASAR_SECRET_KEY}:".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def create_payment(
    user_id: str,
    plan_tier: str,
    billing_cycle: str = "monthly",
) -> dict:
    """
    Create a Moyasar payment for a subscription.
    Returns payment URL for 3DS redirect.
    """
    sb = get_supabase()
    if not sb:
        raise ValueError("خدمة الدفع غير متوفرة حالياً")

    if not MOYASAR_SECRET_KEY:
        raise ValueError("بوابة الدفع غير مفعّلة — تواصل مع الإدارة")

    # Get plan details
    plan_result = (
        sb.table("subscription_plans")
        .select("*")
        .eq("tier", plan_tier)
        .eq("is_active", True)
        .single()
        .execute()
    )
    plan = plan_result.data
    if not plan:
        raise ValueError(f"الباقة '{plan_tier}' غير موجودة")

    if plan["price_monthly_sar"] == 0:
        raise ValueError("الباقة المجانية لا تتطلب دفع")

    # Calculate amount in halalas (smallest unit)
    if billing_cycle == "yearly":
        amount = plan["price_yearly_sar"] * 100  # SAR to halalas
    else:
        amount = plan["price_monthly_sar"] * 100

    # Record payment transaction as initiated
    tx_result = (
        sb.table("payment_transactions")
        .insert({
            "user_id": user_id,
            "amount_sar": amount // 100,
            "status": "initiated",
            "metadata": {
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle,
                "plan_id": plan["id"],
            },
        })
        .execute()
    )
    tx_id = tx_result.data[0]["id"]

    # Create Moyasar payment
    callback_url = f"{MOYASAR_CALLBACK_URL}?tx_id={tx_id}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MOYASAR_API_BASE}/payments",
            headers=_moyasar_auth_header(),
            json={
                "amount": amount,
                "currency": "SAR",
                "description": f"اشتراك سند AI — {plan['name_ar']} ({billing_cycle})",
                "callback_url": callback_url,
                "metadata": {
                    "user_id": user_id,
                    "plan_tier": plan_tier,
                    "billing_cycle": billing_cycle,
                    "tx_id": tx_id,
                },
                "source": {
                    "type": "creditcard",
                    "name": "Sanad AI Subscription",
                    "number": "required_at_frontend",
                    "cvc": "required_at_frontend",
                    "month": "required_at_frontend",
                    "year": "required_at_frontend",
                },
            },
        )

    if response.status_code not in (200, 201):
        print(f"Moyasar create payment error: {response.text}")
        raise ValueError("فشل إنشاء عملية الدفع — حاول مرة أخرى")

    payment_data = response.json()

    # Update transaction with Moyasar payment ID
    sb.table("payment_transactions").update({
        "moyasar_payment_id": payment_data.get("id"),
    }).eq("id", tx_id).execute()

    return {
        "payment_id": payment_data.get("id"),
        "payment_url": payment_data.get("source", {}).get("transaction_url"),
        "tx_id": tx_id,
        "amount_sar": amount // 100,
        "plan": plan["name_ar"],
    }


async def create_payment_form_data(
    user_id: str,
    plan_tier: str,
    billing_cycle: str = "monthly",
) -> dict:
    """
    Get data needed for Moyasar frontend form (Moyasar.js).
    Instead of server-side payment creation, return data for client-side form.
    """
    sb = get_supabase()
    if not sb:
        raise ValueError("خدمة الدفع غير متوفرة حالياً")

    # Get plan details
    plan_result = (
        sb.table("subscription_plans")
        .select("*")
        .eq("tier", plan_tier)
        .eq("is_active", True)
        .single()
        .execute()
    )
    plan = plan_result.data
    if not plan:
        raise ValueError(f"الباقة '{plan_tier}' غير موجودة")

    if plan["price_monthly_sar"] == 0:
        raise ValueError("الباقة المجانية لا تتطلب دفع")

    # Calculate amount in halalas
    if billing_cycle == "yearly":
        amount = plan["price_yearly_sar"] * 100
    else:
        amount = plan["price_monthly_sar"] * 100

    # Record payment as initiated
    tx_result = (
        sb.table("payment_transactions")
        .insert({
            "user_id": user_id,
            "amount_sar": amount // 100,
            "status": "initiated",
            "metadata": {
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle,
                "plan_id": plan["id"],
            },
        })
        .execute()
    )
    tx_id = tx_result.data[0]["id"]

    callback_url = f"{MOYASAR_CALLBACK_URL}?tx_id={tx_id}"

    return {
        "tx_id": tx_id,
        "amount": amount,
        "currency": "SAR",
        "description": f"اشتراك سند AI — {plan['name_ar']}",
        "callback_url": callback_url,
        "metadata": {
            "user_id": user_id,
            "plan_tier": plan_tier,
            "billing_cycle": billing_cycle,
            "tx_id": tx_id,
        },
        "plan": {
            "tier": plan_tier,
            "name_ar": plan["name_ar"],
            "price_sar": amount // 100,
        },
    }


async def verify_payment(payment_id: str, tx_id: Optional[str] = None) -> dict:
    """
    Verify a payment with Moyasar and activate subscription if paid.
    Called after 3DS redirect back to our app.
    """
    if not MOYASAR_SECRET_KEY:
        raise ValueError("بوابة الدفع غير مفعّلة")

    # Fetch payment status from Moyasar
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MOYASAR_API_BASE}/payments/{payment_id}",
            headers=_moyasar_auth_header(),
        )

    if response.status_code != 200:
        print(f"Moyasar verify error: {response.text}")
        raise ValueError("فشل التحقق من عملية الدفع")

    payment = response.json()
    status = payment.get("status")
    metadata = payment.get("metadata", {})

    sb = get_supabase()
    if not sb:
        raise ValueError("خدمة قاعدة البيانات غير متوفرة")

    # Update transaction
    update_data = {
        "moyasar_payment_id": payment_id,
        "status": "paid" if status == "paid" else "failed",
        "payment_method": payment.get("source", {}).get("type", "unknown"),
    }

    if tx_id:
        sb.table("payment_transactions").update(update_data).eq("id", tx_id).execute()
    else:
        sb.table("payment_transactions").update(update_data).eq("moyasar_payment_id", payment_id).execute()

    if status == "paid":
        # Activate subscription
        user_id = metadata.get("user_id")
        plan_tier = metadata.get("plan_tier")
        billing_cycle = metadata.get("billing_cycle", "monthly")

        if user_id and plan_tier:
            await _activate_subscription(user_id, plan_tier, billing_cycle, payment_id, tx_id)

        return {"status": "paid", "message": "تم تفعيل الاشتراك بنجاح!"}
    else:
        return {"status": status, "message": "فشلت عملية الدفع — حاول مرة أخرى"}


async def cancel_subscription(user_id: str) -> dict:
    """
    Cancel user's active subscription at end of current period.
    The subscription stays active until current_period_end.
    """
    sb = get_supabase()
    if not sb:
        raise ValueError("الخدمة غير متوفرة حالياً")

    # Find active subscription
    result = (
        sb.table("user_subscriptions")
        .select("id, plan_id, current_period_end")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )

    if not result.data:
        raise ValueError("لا يوجد اشتراك فعال للإلغاء")

    sub = result.data[0]

    # Check if it's a free plan (don't cancel free)
    plan_result = (
        sb.table("subscription_plans")
        .select("tier")
        .eq("id", sub["plan_id"])
        .single()
        .execute()
    )
    if plan_result.data and plan_result.data["tier"] == "free":
        raise ValueError("لا يمكن إلغاء الباقة المجانية")

    # Mark for cancellation at end of period
    sb.table("user_subscriptions").update({
        "cancel_at_period_end": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sub["id"]).execute()

    return {
        "status": "canceled",
        "message": f"سيتم إلغاء اشتراكك في نهاية الفترة الحالية ({sub['current_period_end'][:10]})",
        "active_until": sub["current_period_end"],
    }


async def handle_webhook(payload: dict) -> dict:
    """
    Process Moyasar webhook callback.
    This is a backup confirmation — verify_payment is the primary flow.
    """
    event_type = payload.get("type")
    data = payload.get("data", {})
    payment_id = data.get("id")

    if not payment_id:
        return {"status": "ignored", "reason": "no payment_id"}

    if event_type == "payment_paid":
        return await verify_payment(payment_id)
    elif event_type == "payment_failed":
        sb = get_supabase()
        if sb:
            sb.table("payment_transactions").update({
                "status": "failed",
            }).eq("moyasar_payment_id", payment_id).execute()
        return {"status": "recorded", "event": "payment_failed"}

    return {"status": "ignored", "event": event_type}


# ---- Internal helpers ----

async def _activate_subscription(
    user_id: str,
    plan_tier: str,
    billing_cycle: str,
    payment_id: str,
    tx_id: Optional[str] = None,
) -> None:
    """Create or update user subscription after successful payment."""
    sb = get_supabase()
    if not sb:
        return

    # Get plan ID
    plan_result = (
        sb.table("subscription_plans")
        .select("id")
        .eq("tier", plan_tier)
        .single()
        .execute()
    )
    if not plan_result.data:
        print(f"Plan not found: {plan_tier}")
        return

    plan_id = plan_result.data["id"]
    now = datetime.now(timezone.utc)

    # Calculate period end
    if billing_cycle == "yearly":
        period_end = now + timedelta(days=365)
    else:
        period_end = now + timedelta(days=30)

    # Deactivate any existing active subscription
    sb.table("user_subscriptions").update({
        "status": "expired",
        "updated_at": now.isoformat(),
    }).eq("user_id", user_id).eq("status", "active").execute()

    # Create new subscription
    sub_result = (
        sb.table("user_subscriptions")
        .insert({
            "user_id": user_id,
            "plan_id": plan_id,
            "status": "active",
            "billing_cycle": billing_cycle,
            "moyasar_payment_id": payment_id,
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "cancel_at_period_end": False,
        })
        .execute()
    )

    # Link transaction to subscription
    if tx_id and sub_result.data:
        sub_id = sub_result.data[0]["id"]
        sb.table("payment_transactions").update({
            "subscription_id": sub_id,
        }).eq("id", tx_id).execute()

    print(f"✅ Subscription activated: user={user_id}, plan={plan_tier}, cycle={billing_cycle}")
