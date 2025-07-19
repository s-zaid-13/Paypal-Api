import requests
from paypal_auth import get_paypal_access_token


def get_capture_id(subscription_id):
    access_token = get_paypal_access_token()

    from datetime import datetime, timedelta

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    url = f"https://api.sandbox.paypal.com/v1/billing/subscriptions/{subscription_id}/transactions"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z",
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    print("Response: ", data)
    for txn in data.get("transactions", []):
        return txn.get("id")
