"""
PayPal payment gateway integration.
Uses PayPal Orders API v2 for checkout.

Flow:
1. Frontend calls create_order → returns order_id
2. User approves in PayPal popup (client-side JS SDK)
3. Frontend calls capture_order → captures payment, activates subscription
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from backend.config import PAYPAL_CLIENT_ID, PAYPAL_SECRET_KEY, PAYPAL_MODE
from backend.db import get_supabase

log = logging.getLogger("sanad.paypal")

# API base URLs
PAYPAL_API_BASE = (
    "https://api-m.paypal.com"
    if PAYPAL_MODE == "live"
    else "https://api-m.sandbox.paypal.com"
)


async def _get_access_token() -> str:
    """Get PayPal OAuth2 access token using client credentials."""
    if not PAYPAL_CLIENT_ID or not PAYPAL_SECRET_KEY:
        raise ValueError("PayPal غير مفعّل — تواصل مع الإدارة")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET_KEY),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        log.error("PayPal auth error: %s", response.text)
        raise ValueError("فشل الاتصال ببوابة PayPal")

    return response.json()["access_token"]


async def create_order(
    user_id: str,
    plan_tier: str,
    billing_cycle: str = "monthly",
) -> dict:
    """
    Create a PayPal order for subscription payment.
    Returns order_id for client-side approval.
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

    # Calculate amount in SAR
    if billing_cycle == "yearly":
        amount_sar = plan["price_yearly_sar"]
    else:
        amount_sar = plan["price_monthly_sar"]

    # Convert SAR to USD for PayPal (1 USD = 3.75 SAR)
    SAR_TO_USD = 3.75
    amount_usd = round(float(amount_sar) / SAR_TO_USD, 2)

    # Record payment transaction as initiated
    tx_result = (
        sb.table("payment_transactions")
        .insert({
            "user_id": user_id,
            "amount_sar": amount_sar,
            "status": "initiated",
            "payment_method": "paypal",
            "metadata": {
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle,
                "plan_id": plan["id"],
                "gateway": "paypal",
            },
        })
        .execute()
    )
    tx_id = tx_result.data[0]["id"]

    # Get PayPal access token
    access_token = await _get_access_token()

    # Create PayPal order
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": tx_id,
                        "description": f"اشتراك سند AI — {plan['name_ar']}",
                        "amount": {
                            "currency_code": "USD",
                            "value": str(amount_usd),
                        },
                        "custom_id": f"{user_id}|{plan_tier}|{billing_cycle}|{tx_id}",
                    }
                ],
            },
        )

    if response.status_code not in (200, 201):
        log.error("PayPal create order error: %s", response.text)
        # Clean up initiated transaction
        sb.table("payment_transactions").update({
            "status": "failed",
        }).eq("id", tx_id).execute()
        raise ValueError("فشل إنشاء طلب الدفع عبر PayPal — حاول مرة أخرى")

    order_data = response.json()
    order_id = order_data["id"]

    # Update transaction with PayPal order ID
    sb.table("payment_transactions").update({
        "moyasar_payment_id": order_id,  # Reuse this field for PayPal order ID
    }).eq("id", tx_id).execute()

    log.info(
        "PayPal order created: order=%s, user=%s, plan=%s, amount=%s SAR",
        order_id, user_id[:8], plan_tier, amount_sar,
    )

    return {
        "order_id": order_id,
        "tx_id": tx_id,
        "amount_sar": amount_sar,
        "plan": plan["name_ar"],
    }


async def capture_order(order_id: str) -> dict:
    """
    Capture an approved PayPal order and activate subscription.
    Called after user approves payment in PayPal popup.
    """
    if not order_id:
        raise ValueError("معرّف الطلب مطلوب")

    # Get PayPal access token
    access_token = await _get_access_token()

    # Capture the payment
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code not in (200, 201):
        log.error("PayPal capture error: %s", response.text)
        raise ValueError("فشل تأكيد الدفع — حاول مرة أخرى")

    capture_data = response.json()
    status = capture_data.get("status")

    if status != "COMPLETED":
        log.warning("PayPal order not completed: status=%s", status)
        raise ValueError(f"حالة الدفع: {status} — لم يكتمل الدفع")

    # Extract metadata from custom_id
    purchase_unit = capture_data.get("purchase_units", [{}])[0]
    capture_info = purchase_unit.get("payments", {}).get("captures", [{}])[0]
    custom_id = capture_info.get("custom_id", "")

    if not custom_id:
        # Fallback: try from purchase unit directly
        custom_id = purchase_unit.get("custom_id", "")

    parts = custom_id.split("|")
    if len(parts) < 4:
        log.error("Invalid custom_id in PayPal capture: %s", custom_id)
        raise ValueError("بيانات الدفع غير صالحة")

    user_id, plan_tier, billing_cycle, tx_id = parts[0], parts[1], parts[2], parts[3]

    sb = get_supabase()
    if not sb:
        raise ValueError("خدمة قاعدة البيانات غير متوفرة")

    # Verify captured amount matches the expected plan price
    captured_amount = capture_info.get("amount", {})
    captured_value = float(captured_amount.get("value", "0"))

    # Look up expected price from transaction record
    tx_result = sb.table("payment_transactions").select("amount_sar").eq("id", tx_id).single().execute()
    if tx_result.data:
        expected_sar = float(tx_result.data["amount_sar"])
        SAR_TO_USD = 3.75
        expected_usd = round(expected_sar / SAR_TO_USD, 2)
        # Allow 1 cent tolerance for rounding
        if abs(captured_value - expected_usd) > 0.02:
            log.error(
                "PayPal amount mismatch: captured=%.2f USD, expected=%.2f USD (%.0f SAR), order=%s",
                captured_value, expected_usd, expected_sar, order_id,
            )
            sb.table("payment_transactions").update({
                "status": "amount_mismatch",
                "payment_method": "paypal",
            }).eq("id", tx_id).execute()
            raise ValueError("المبلغ المدفوع لا يطابق سعر الباقة")

    # Update transaction status
    sb.table("payment_transactions").update({
        "status": "paid",
        "payment_method": "paypal",
    }).eq("id", tx_id).execute()

    # Activate subscription using shared function from payment.py
    from backend.services.payment import _activate_subscription
    await _activate_subscription(
        user_id=user_id,
        plan_tier=plan_tier,
        billing_cycle=billing_cycle,
        payment_id=order_id,
        tx_id=tx_id,
    )

    log.info(
        "PayPal payment completed: order=%s, user=%s, plan=%s",
        order_id, user_id[:8], plan_tier,
    )

    return {
        "status": "paid",
        "message": "تم تفعيل الاشتراك بنجاح!",
        "plan_tier": plan_tier,
    }
