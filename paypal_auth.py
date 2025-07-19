import requests
import time
from django.conf import settings

TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0,
}


def get_paypal_access_token():
    now = int(time.time())

    if TOKEN_CACHE["access_token"] and now < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["access_token"]

    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    base_url = settings.PAYPAL_BASE_URL

    token_url = f"{base_url}/v1/oauth2/token"
    token_payload = {"grant_type": "client_credentials"}
    token_headers = {"Accept": "application/json", "Accept-Language": "en_US"}

    response = requests.post(
        token_url,
        auth=(client_id, client_secret),
        data=token_payload,
        headers=token_headers,
    )

    if response.status_code != 200:
        raise Exception("Failed to obtain PayPal access token")

    res_data = response.json()
    access_token = res_data["access_token"]
    expires_in = res_data.get("expires_in", 3600)

    TOKEN_CACHE["access_token"] = access_token
    TOKEN_CACHE["expires_at"] = now + expires_in - 60

    return access_token
