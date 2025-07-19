from django.core.management.base import BaseCommand
from accounts.models import User
from transactions.models import Transaction
from subscriptions.utils import fetch_paypal_subscription
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta


class Command(BaseCommand):
    help = "Audit PayPal subscriptions and detect skipped/missed billing"

    def handle(self, *args, **kwargs):
        active_users = User.objects.filter(is_subscribed=True)
        for user in active_users:
            print("hello")
            subscription_id = user.paypal_subscription_id
            if not subscription_id:
                continue

            paypal_data = fetch_paypal_subscription(subscription_id)
            print(paypal_data)
            if not paypal_data:
                self.stdout.write(f"❌ Could not fetch PayPal data for {user.email}")
                continue

            status = paypal_data.get("status")
            billing_info = paypal_data.get("billing_info", {})
            last_payment_info = billing_info.get("last_payment", {})
            last_payment_time = last_payment_info.get("time")

            # Parse and compare with DB
            if last_payment_time:
                last_payment_time = parse_datetime(last_payment_time)

                local_txn = (
                    Transaction.objects.filter(
                        user=user, transaction_type="subscription", status="success"
                    )
                    .order_by("-created_at")
                    .first()
                )

                if not local_txn or (
                    local_txn and local_txn.created_at != last_payment_time
                ):
                    self.stdout.write(
                        f"⚠️ Missed webhook for {user.email}, logging manually..."
                    )

                    Transaction.objects.create(
                        transaction_id=f"{subscription_id}-SYNC",
                        payer_name=user.get_full_name(),
                        payer_email=user.email,
                        amount=last_payment_info["amount"]["value"],
                        currency=last_payment_info["amount"]["currency_code"],
                        transaction_type="subscription",
                        product=None,
                        status="success",
                        created_at=last_payment_time,
                    )
                now_date = now()
                expected_next_payment = last_payment_time + relativedelta(
                    months=1
                )  # or weeks/days

                if now_date > expected_next_payment:
                    self.stdout.write(
                        f"⛔ Skipped billing cycle detected for {user.email}"
                    )
                    user.is_subscribed = False
                    user.save()
            else:
                self.stdout.write(
                    f"No payment yet for {user.email}, possibly trial or not charged"
                )

            # Revoke access if status is NOT active
            if status != "ACTIVE":
                user.is_subscribed = False
                user.save()
                self.stdout.write(
                    f"⛔ Subscription not active. Revoked access for {user.email}"
                )
