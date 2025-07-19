import requests
from django.conf import settings
from paypal_auth import get_paypal_access_token
from .models import Plan


def create_paypal_product(name="Premium Access", description="Premium subscription"):
    access_token = get_paypal_access_token()
    base_url = settings.PAYPAL_BASE_URL

    url = f"{base_url}/v1/catalogs/products"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    data = {
        "name": name,
        "description": description,
        "type": "SERVICE",
        "category": "SOFTWARE",
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 201:
        return None, response.json()

    return response.json()["id"], None


def create_paypal_plan(product_id, name, description, price, billing_interval):
    access_token = get_paypal_access_token()
    base_url = settings.PAYPAL_BASE_URL

    url = f"{base_url}/v1/billing/plans"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    data = {
        "product_id": product_id,
        "name": name,
        "description": description,
        "status": "ACTIVE",
        "billing_cycles": [
            {
                "frequency": {"interval_unit": billing_interval, "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {"value": price, "currency_code": "USD"}
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee": {"value": "0", "currency_code": "USD"},
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
        "taxes": {"percentage": "0", "inclusive": False},
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
        return None, response.json()
    print(response.json())

    paypal_plan_id = response.json()["id"]
    plan = Plan.objects.create(
        name=name,
        description=description,
        price=price,
        billing_interval=billing_interval,
        paypal_plan_id=paypal_plan_id,
        is_active=True,
    )

    return {
        "paypal_plan_id": paypal_plan_id,
        "product_id": product_id,
        "plan_id": plan.id,
        "msg": "✅ Plan created and stored successfully",
    }, None
