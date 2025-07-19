from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CreateSubscriptionSerializer, ReviseSubscriptionSerializer
from .utils import (
    create_paypal_subscription,
    get_client_ip,
    cancel_paypal_subscription,
    refund_paypal_payment,
    reactivate_paypal_subscription,
    pause_paypal_subscription,
    revise_paypal_subscription,
)
from django.utils import timezone
from plans.models import Plan
from accounts.models import User
from django.shortcuts import render
from transactions.models import Transaction
from django.contrib.auth.decorators import login_required


class CreateSubscriptionView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        print("ip: ", ip)
        recent_trial_exists = Transaction.objects.filter(
            ip_address=ip,
            transaction_type="subscription",
            # amount=0,
        ).exists()

        if recent_trial_exists:
            return Response(
                {"error": "Free trial already used from this IP"}, status=400
            )

        user = request.user
        user.trial_ip = ip
        user.save()

        if request.user.is_subscribed:
            return Response({"detail": "User is already subscribed."}, status=400)

        if user.subscription_pending:
            return Response(
                {
                    "error": "You already have a subscription process in progress. Complete or cancel that first."
                },
                status=400,
            )

        serializer = CreateSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            plan_id = serializer.validated_data["plan_id"]
            try:
                result, error = create_paypal_subscription(plan_id)

                if error:
                    return Response({"error": error}, status=400)
            except Exception as error:
                return Response({"error": str(error)}, status=500)

            user = User.objects.get(username=request.user.username)
            user.paypal_subscription_id = result["subscription_id"]
            user.subscription_pending = True
            user.paypal_plan_id = plan_id
            user.save()

            return Response(result, status=201)

        return Response(serializer.errors, status=400)


class CancelSubscriptionView(APIView):
    def post(self, request):
        user = request.user

        if not user.is_subscribed and not user.paypal_subscription_id:
            return Response({"error": "No active subscription"}, status=400)

        success = cancel_paypal_subscription(user.paypal_subscription_id)

        if success:
            return Response(
                {"message": "Subscription cancelled. Access will be removed shortly."}
            )
        else:
            return Response({"error": "Failed to cancel subscription"}, status=500)


class CancelPendingSubscriptionView(APIView):
    def post(self, request):
        user = request.user
        if not user.subscription_pending:
            return Response({"error": "No pending subscription to cancel."}, status=400)

        user.subscription_pending = False
        user.paypal_subscription_id = None
        user.save()
        return Response({"message": "Pending subscription has been cancelled."})


class RefundPaymentView(APIView):

    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        user = request.user
        try:
            txn = Transaction.objects.get(transaction_id=transaction_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=404)

        if not txn.capture_id:
            return Response({"error": "No capture_id to refund"}, status=400)
        if txn.transaction_type == "subscription":
            capture_id = txn.capture_id
            full_amount = float(txn.amount)
            paid_on = txn.created_at
            now = timezone.now()

            # Get interval from previous plan
            try:
                plan = Plan.objects.get(paypal_plan_id=user.paypal_plan_id)
                interval = plan.billing_interval
            except Plan.DoesNotExist:
                print("Plan not exist")
            total_days = 365 if interval == "YEAR" else 30

            days_used = (now - paid_on).days
            used_amount = min(days_used * (full_amount / total_days), full_amount)
            refund_amount = full_amount - used_amount
        else:
            refund_amount = txn.amount
        success, response_data = refund_paypal_payment(capture_id, refund_amount)

        if success:
            txn.status = "refunded"
            txn.save()
            return Response(
                {"message": "Payment refunded", "paypal_response": response_data}
            )
        else:
            return Response(
                {"error": "Refund failed", "paypal_response": response_data}, status=500
            )


from paypal_auth import get_paypal_access_token
from webhooks.utils import get_capture_id


# @login_required
def subscription_success(request):
    get_capture_id("I-RESX5LLE810R")
    return render(request, "subscription_success.html")


# @login_required
def subscription_cancel(request):
    return render(request, "subscription_cancel.html")


class ShiftSubscriptionView(APIView):
    def post(self, request):
        user = request.user
        new_plan_id = request.data.get("new_plan_id")

        if not new_plan_id:
            return Response({"error": "new_plan_id is required"}, status=400)

        if not (user.is_subscribed and user.paypal_subscription_id):
            return Response({"error": "User has no active subscription."}, status=400)

        try:
            new_plan = Plan.objects.get(paypal_plan_id=new_plan_id, is_active=True)
        except Plan.DoesNotExist:
            return Response({"error": "Invalid plan selected"}, status=400)

        try:
            last_txn = Transaction.objects.filter(
                user=user, transaction_type="subscription"
            ).latest("created_at")
        except Transaction.DoesNotExist:
            return Response({"error": "No previous transaction found"}, status=404)

        capture_id = last_txn.capture_id
        full_amount = float(last_txn.amount)
        paid_on = last_txn.created_at
        now = timezone.now()

        # Get interval from previous plan
        try:
            plan = Plan.objects.get(paypal_plan_id=user.paypal_plan_id)
            interval = plan.billing_interval
        except Plan.DoesNotExist:
            print("Plan not exist")
        total_days = 365 if interval == "YEAR" else 30

        days_used = (now - paid_on).days
        used_amount = min(days_used * (full_amount / total_days), full_amount)
        refund_amount = full_amount - used_amount

        cancel_success = cancel_paypal_subscription(user.paypal_subscription_id)
        if not cancel_success:
            return Response({"error": "Failed to cancel old subscription"}, status=500)

        refund_success, refund_data = refund_paypal_payment(
            capture_id,
            refund_amount,
        )

        user.is_subscribed = False
        user.paypal_subscription_id = None
        user.save()

        ip = get_client_ip(request)
        print("ip: ", ip)
        recent_trial_exists = Transaction.objects.filter(
            ip_address=ip,
            transaction_type="subscription",
            amount=0,
        ).exists()

        if recent_trial_exists:
            return Response(
                {"error": "Free trial already used from this IP"}, status=400
            )

        user = request.user
        user.trial_ip = ip
        user.save()

        if user.subscription_pending:
            return Response(
                {
                    "error": "You already have a subscription process in progress. Complete or cancel that first."
                },
                status=400,
            )
        result, error = create_paypal_subscription(new_plan_id)
        if error:
            return Response({"error": error}, status=400)
        user.subscription_pending = True
        user.paypal_subscription_id = result["subscription_id"]
        user.subscription_pending = True
        user.paypal_plan_id = new_plan_id
        user.save()
        return Response(
            {
                "message": "Old subscription cancelled. Partial refund issued.",
                "refunded_amount": f"{refund_amount:.2f} {last_txn.currency}",
                "new_approval_url": result["approval_url"],
                "subscription_note": result["msg"],
            },
            status=200,
        )


class PauseSubscriptionView(APIView):
    def post(self, request):
        user = request.user
        if not user.is_authenticated or not user.is_subscribed:
            return Response({"error": "No active subscription"}, status=400)

        success, message = pause_paypal_subscription(user.paypal_subscription_id)
        if success:
            user.is_subscribed = False
            user.save()
            return Response({"message": message})
        return Response({"error": message}, status=400)


class ReactivateSubscriptionView(APIView):
    def post(self, request):
        user = request.user
        if not user.is_authenticated or not user.paypal_subscription_id:
            return Response({"error": "No subscription to reactivate"}, status=400)

        success, message = reactivate_paypal_subscription(user.paypal_subscription_id)
        if success:
            user.is_subscribed = True
            user.save()
            return Response({"message": message})
        return Response({"error": message}, status=400)


class ReviseSubscriptionView(APIView):
    def post(self, request):
        serializer = ReviseSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            subscription_id = serializer.validated_data["subscription_id"]
            new_plan_id = serializer.validated_data["new_plan_id"]

            try:
                result = revise_paypal_subscription(subscription_id, new_plan_id)

                # Extract approval link
                approval_url = next(
                    (
                        link["href"]
                        for link in result.get("links", [])
                        if link["rel"] == "approve"
                    ),
                    None,
                )

                if not approval_url:
                    return Response({"error": "Approval URL not found"}, status=400)

                return Response(
                    {
                        "message": "Subscription revision initiated. User must approve.",
                        "approval_url": approval_url,
                        "subscription_id": subscription_id,
                        "new_plan_id": new_plan_id,
                    }
                )

            except Exception as e:
                return Response({"error": str(e)}, status=500)

        return Response(serializer.errors, status=400)
