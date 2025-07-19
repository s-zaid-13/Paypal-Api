from paypalcheckoutsdk.orders import (
    OrdersCreateRequest,
    OrdersCaptureRequest,
    OrdersGetRequest,
)
from decimal import Decimal, ROUND_HALF_UP
from paypal_client import PayPalClient
from products.models import Product
from transactions.models import Transaction
from rest_framework.exceptions import ValidationError
from paypalhttp import HttpError
from .models import PendingOrder
from django.conf import settings

PAYPAL_SUPPORTED_CURRENCIES = [
    "AUD",  # Australian Dollar
    "BRL",  # Brazilian Real
    "CAD",  # Canadian Dollar
    "CNY",  # Chinese Renminbi
    "CZK",  # Czech Koruna
    "DKK",  # Danish Krone
    "EUR",  # Euro
    "HKD",  # Hong Kong Dollar
    "HUF",  # Hungarian Forint
    "ILS",  # Israeli New Shekel
    "JPY",  # Japanese Yen
    "MYR",  # Malaysian Ringgit
    "MXN",  # Mexican Peso
    "TWD",  # New Taiwan Dollar
    "NZD",  # New Zealand Dollar
    "NOK",  # Norwegian Krone
    "PHP",  # Philippine Peso
    "PLN",  # Polish Złoty
    "GBP",  # Pound Sterling
    "SGD",  # Singapore Dollar
    "SEK",  # Swedish Krona
    "CHF",  # Swiss Franc
    "THB",  # Thai Baht
    "USD",  # United States Dollar
]


def rounded_amount(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_paypal_order(user, items_data, currency="USD"):
    purchase_items = []
    item_total = Decimal("0.00")

    currency = currency.upper()

    if currency not in PAYPAL_SUPPORTED_CURRENCIES:
        return None, f"Currency '{currency}' is not supported by PayPal."

    products_in_order = []
    for item in items_data:
        try:
            product = Product.objects.get(id=item["product_id"], is_active=True)
        except Product.DoesNotExist:
            return None, f"Invalid product ID: {item['product_id']}"

        quantity = item["quantity"]
        total_price = Decimal(product.price) * quantity
        item_total += total_price

        purchase_items.append(
            {
                "name": product.name,
                "description": product.description,
                "quantity": str(quantity),
                "unit_amount": {
                    "currency_code": currency,
                    "value": str(product.price),
                },
            }
        )
        products_in_order.append(product)

    total_str = str(rounded_amount(item_total))

    request = OrdersCreateRequest()
    request.prefer("return=representation")
    request.request_body(
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": "Multiple Product Order",
                    "amount": {
                        "currency_code": currency,
                        "value": total_str,
                        "breakdown": {
                            "item_total": {
                                "currency_code": currency,
                                "value": total_str,
                            }
                        },
                    },
                    "items": purchase_items,
                }
            ],
            "application_context": {
                "return_url": "http://localhost:8000/payment/success/",
                "cancel_url": "http://localhost:8000/payment/cancel/",
                "brand_name": "Future Store",
            },
        }
    )

    client = PayPalClient().client

    response = client.execute(request)

    approve_url = next(
        link.href for link in response.result.links if link.rel == "approve"
    )

    pending = PendingOrder.objects.create(
        user=user if user.is_authenticated else None,
        order_id=response.result.id,
        total_amount=item_total,
    )
    pending.products.set(products_in_order)

    return {
        "order_id": response.result.id,
        "approve_url": approve_url,
        "msg": "✅ Order created successfully. Visit approval URL to proceed.",
    }, None


def capture_paypal_order(user, order_id):
    if Transaction.objects.filter(transaction_id=order_id).exists():
        raise ValidationError("This order has already been captured.")

    request = OrdersCaptureRequest(order_id)
    request.request_body({})

    try:
        client = PayPalClient().client
        response = client.execute(request)
    except HttpError as e:
        if e.status_code == 422:
            return {
                "error": " Payment token invalid or already used",
                "details": str(e.message),
            }
        return {"error": "Payment failed. Please try again.", "details": str(e.message)}
    result = response.result

    if result.status != "COMPLETED":
        return {
            "error": f"Payment status is {result.status}. Transaction was not completed."
        }

    payer = result.payer
    purchase_unit = result.purchase_units[0]
    capture = purchase_unit.payments.captures[0]
    amount = capture.amount
    rounded_value = rounded_amount(amount.value)
    PendingOrder.objects.filter(order_id=order_id).update(is_completed=True)

    Transaction.objects.create(
        transaction_id=result.id,
        payer_name=f"{payer.name.given_name} {payer.name.surname}",
        payer_email=payer.email_address,
        capture_id=purchase_unit.payments.captures[0].id,
        amount=rounded_value,
        status=result.status,
        currency=amount.currency_code,
        user=user,
        transaction_type="one_time",
        product=None,
    )

    return {
        "status": result.status,
        "transaction_id": result.id,
        "payer_name": f"{payer.name.given_name} {payer.name.surname}",
        "payer_email": payer.email_address,
        "amount": rounded_value,
        "currency": amount.currency_code,
    }


def get_paypal_order_details(order_id):
    client = PayPalClient().client
    request = OrdersGetRequest(order_id)

    try:
        response = client.execute(request)
        result = response.result
        print(result)

        return {
            "status": result.status,
            "order_id": result.id,
            "amount": result.purchase_units[0].amount.value,
            "currency": result.purchase_units[0].amount.currency_code,
        }

    except Exception as e:
        return {"error": str(e)}
