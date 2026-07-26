"""Razorpay test-mode integration for the mocked rail (§12). Test mode only -
no real money moves. Uses the Orders API rather than Payouts/RazorpayX: this
product is a payout (paying a payee), but Payouts requires a separate
RazorpayX business-banking account with its own onboarding, while Orders
works with a plain key_id/key_secret pair and gives a real Razorpay-issued
transaction reference (order_id) to use as the demo's txn_id - which is the
actual goal here (a real gateway touchpoint on stage), not literally
completing a checkout, which doesn't fit a voice-only IVR anyway.

If this call fails (network hiccup, bad credentials), callers fall back to
a locally generated txn_id rather than blocking the whole transfer on a
payment-gateway dependency mid-demo.
"""
import httpx

from app.config import settings

_ORDERS_URL = "https://api.razorpay.com/v1/orders"


def create_order(amount_paise: int, receipt: str, notes: dict) -> str:
    """Returns a Razorpay order_id, or raises on failure - caller decides the
    fallback behaviour."""
    resp = httpx.post(
        _ORDERS_URL,
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
        json={"amount": amount_paise, "currency": "INR", "receipt": receipt, "notes": notes},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()["id"]
