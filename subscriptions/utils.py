from paypal_auth import get_paypal_access_token
from plans.models import Plan
from transactions.models import Transaction
import requests
from django.conf import settings


def create_paypal_subscription(plan_id):
    try:
        plan = Plan.objects.get(paypal_plan_id=plan_id, is_active=True)
    except Plan.DoesNotExist:
        return None, "Invalid plan"

    access_token = get_paypal_access_token()
    base_url = settings.PAYPAL_BASE_URL

    url = f"{base_url}/v1/billing/subscriptions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    data = {
        "plan_id": plan_id,
        "application_context": {
            "brand_name": "Future Store",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": "http://localhost:8000/subscription/success/",
            "cancel_url": "http://localhost:8000/subscription/cancel/",
        },
    }

    try:
        response = requests.post(url=url, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            return None, "Too many requests. Try again after some time."
        elif response.status_code == 422:
            return None, "Unprocessable request. Possibly sandbox limit reached."
        return None, f"PayPal error: {e}"
    if response.status_code != 201:
        return "Failed to create PayPal payment", None

    result = response.json()

    approval_url = next(
        (link["href"] for link in result.get("links", []) if link["rel"] == "approve"),
        None,
    )

    return {
        "subscription_id": result["id"],
        "approval_url": approval_url,
        "plan_name": plan.name,
        "price": plan.price,
        "interval": plan.billing_interval,
        "msg": "Go to approve_url to active your subscription",
    }, None


def cancel_paypal_subscription(subscription_id):
    access_token = get_paypal_access_token()
    base_url = settings.PAYPAL_BASE_URL

    url = f"{base_url}/v1/billing/subscriptions/{subscription_id}/cancel"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    data = {"reason": "User-initiated cancellation"}
    try:
        response = requests.post(url=url, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            return None, "Too many requests. Try again after some time."
        elif response.status_code == 422:
            return None, "Unprocessable request. Possibly sandbox limit reached."
        return None, f"PayPal error: {e}"
    return response.status_code == 204


def get_client_ip(request):
    """Extract client IP address from request headers (handle proxies)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def refund_paypal_payment(capture_id, amount, reason="User requested refund"):
    access_token = get_paypal_access_token()

    url = f"{settings.PAYPAL_BASE_URL}/v2/payments/captures/{capture_id}/refund"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "amount": {"value": f"{amount:.2f}", "currency_code": "USD"},
        "note_to_payer": reason,
    }
    try:
        response = requests.post(url=url, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            return None, "Too many requests. Try again after some time."
        elif response.status_code == 422:
            return None, "Unprocessable request. Possibly sandbox limit reached."
        return None, f"PayPal error: {e}"
    return response.status_code == 201, response.json()


def fetch_paypal_subscription(subscription_id):
    url = f"{settings.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_paypal_access_token()}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def pause_paypal_subscription(subscription_id, reason="User requested to pause"):
    access_token = get_paypal_access_token()
    url = (
        f"{settings.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}/suspend"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    data = {"reason": reason}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 204:
        return False, response.text
    return True, "Subscription paused successfully"


def reactivate_paypal_subscription(
    subscription_id, reason="User requested reactivation"
):
    access_token = get_paypal_access_token()
    url = f"{settings.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}/activate"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    data = {"reason": reason}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 204:
        return False, response.text
    return True, "Subscription reactivated successfully"


def revise_paypal_subscription(subscription_id, new_plan_id):
    access_token = get_paypal_access_token()
    url = (
        f"{settings.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}/revise"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    payload = {
        "plan_id": new_plan_id,
        "application_context": {
            "brand_name": "Future Store",
            "locale": "en-US",
            "return_url": "https://example.com/",
            "cancel_url": "https://example.com/",
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()
