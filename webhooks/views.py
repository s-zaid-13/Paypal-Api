from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from accounts.models import User
from transactions.models import Transaction
from products.models import Product  # If needed
import json
import uuid
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from plans.models import Plan
from rest_framework.permissions import AllowAny
from rest_framework.authentication import BasicAuthentication
from datetime import timedelta
from django.utils import timezone
from subscriptions.utils import refund_paypal_payment
from .utils import get_capture_id
import time


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def paypal_webhook_view(request):
    try:
        event = json.loads(request.body)
    except Exception as e:
        return Response({"error": "Invalid JSON"}, status=400)

    event_type = event.get("event_type")
    resource = event.get("resource", {})
    print("Webhook-Event: ", event)

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        subscription_id = resource.get("id")
        payer = resource.get("subscriber", {}).get("name", {})
        payer_name = f"{payer.get('given_name', '')} {payer.get('surname', '')}".strip()
        payer_email = resource.get("subscriber", {}).get("email_address")

        amount_obj = (
            resource.get("billing_info", {}).get("last_payment", {}).get("amount", {})
        )
        amount = amount_obj.get("value", "0.00")
        currency = amount_obj.get("currency_code", "USD")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            user.is_subscribed = True
            user.subscription_pending = False
            user.save()
            time.sleep(10)
            capture_id = get_capture_id(subscription_id)
            time.sleep(10)

            Transaction.objects.create(
                transaction_id=subscription_id,
                user=user,
                payer_name=payer_name,
                payer_email=payer_email,
                amount=amount,
                currency=currency,
                capture_id=capture_id,
                transaction_type="subscription",
                ip_address=user.trial_ip,
                product=None,
            )
            print("activate ip address: ", user.trial_ip)
        except User.DoesNotExist:
            print("User does not exist")

    elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            user.paypal_subscription_id = None
            user.subscription_pending = False
            user.is_subscribed = False
            user.save()

            txn = Transaction.objects.filter(transaction_id=subscription_id).first()

            if txn:
                minutes_passed = (timezone.now() - txn.created_at).total_seconds() / 60
                if minutes_passed <= 10 and txn.capture_id:
                    success, refund_response = refund_paypal_payment(
                        txn.capture_id, txn.amount
                    )

                    if success:
                        txn.status = "refunded"
                        txn.save()
                        print("Auto-refunded due to early cancellation.")
                    else:
                        print("Refund failed:", refund_response)

                else:
                    txn.status = "cancelled"
                    txn.save()
                txn.ip_address = None

        except User.DoesNotExist:
            print("User does not exist for cancellation")

    elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")
        amount_obj = resource.get("amount", {})
        amount = amount_obj.get("value", "0.00")
        currency = amount_obj.get("currency_code", "USD")
        try:
            capture_id = get_capture_id(subscription_id)
        except Exception as e:
            capture_id = None
            print(f"Capture_id not found.Detail: {e}")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            if not user.is_subscribed:
                user.is_subscribed = True
            Transaction.objects.create(
                transaction_id=uuid.uuid4().hex,
                user=user,
                payer_name=user.get_full_name() or "N/A",
                payer_email=payer_email,
                amount=amount,
                currency=currency,
                capture_id=capture_id,
                transaction_type="subscription",
                product=None,
            )
        except User.DoesNotExist:
            print("User does not exist")

    elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            # user.is_subscribed = False
            # user.save()

            Transaction.objects.create(
                transaction_id=uuid.uuid4().hex,
                user=user,
                payer_name=user.get("subscriber", {})
                .get("name", {})
                .get("given_name", ""),
                payer_email=payer_email,
                amount=0,
                currency="USD",
                transaction_type="subscription",
                status="failed",
                product=None,
            )
        except User.DoesNotExist:
            print("User not found on first payment failure.")

    elif event_type == "BILLING.SUBSCRIPTION.SUSPENDED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            user.is_subscribed = False
            user.save()

            Transaction.objects.filter(transaction_id=subscription_id).update(
                status="suspended"
            )
        except User.DoesNotExist:
            print("User not found. Subscription suspended")

    elif event_type == "BILLING.SUBSCRIPTION.EXPIRED":
        subscription_id = resource.get("id")
        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            user.is_subscribed = False
            user.paypal_subscription_id = None
            user.save()
            Transaction.objects.filter(transaction_id=subscription_id).update(
                status="expired"
            )
        except User.DoesNotExist:
            print("User not found for expired subscription")

    if event_type in [
        "PAYMENT.CAPTURE.DENIED",
        "RISK.DISPUTED",
        "PAYMENT.DISPUTE.CREATED",
        "PAYMENT.DISPUTE.UPDATED",
    ]:
        transaction_id = resource.get("id") or resource.get(
            "disputed_transactions", [{}]
        )[0].get("seller_transaction_id")

        if transaction_id:
            updated = Transaction.objects.filter(transaction_id=transaction_id).update(
                status=(
                    "disputed"
                    if "DISPUTE" in event_type or "RISK" in event_type
                    else "denied"
                ),
            )
            if updated:
                print(f"Fraud/Dispute detected — transaction flagged: {transaction_id}")
            else:
                print(f"Transaction not found for fraud event: {transaction_id}")

        return Response({"status": "fraud-flagged"})

    elif event_type == "BILLING.SUBSCRIPTION.PRICING_CHANGE.ACTIVATED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")
        new_price_obj = (
            resource.get("billing_info", {}).get("last_payment", {}).get("amount", {})
        )
        new_price = new_price_obj.get("value", "0.00")
        new_currency = new_price_obj.get("currency_code", "USD")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            plan = Plan.objects.get(paypal_plan_id=resource.get("plan_id"))

            plan.price = new_price
            plan.save()
            print(
                f"✅ Pricing updated for user {user.email}. "
                f"New price: {new_price} {new_currency}"
            )

        except User.DoesNotExist:
            print("⚠️ User not found for pricing change webhook.")

        except Plan.DoesNotExist:
            print("⚠️ Plan not found for this webhook.")
    elif event_type == "BILLING.SUBSCRIPTION.UPDATED":
        subscription_id = resource.get("id")
        payer_email = resource.get("subscriber", {}).get("email_address")

        try:
            user = User.objects.get(paypal_subscription_id=subscription_id)
            user.is_subscribed = True  # Mark user as subscribed again
            user.save()
            print(f"✅ Subscription updated and user {user.email} marked as subscribed")
        except User.DoesNotExist:
            print("❌ User not found for subscription update")
    return Response({"status": "received"})
