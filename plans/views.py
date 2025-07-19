from rest_framework import generics
from .models import Plan
from .serializers import PlanSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import create_paypal_product, create_paypal_plan
from .serializers import PlanSerializer
from accounts.models import User


class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer


class CreatePayPalPlanView(APIView):
    def post(self, request):
        product_id, product_err = create_paypal_product()
        if product_err:
            return Response({"error": product_err}, status=400)
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            result, error = create_paypal_plan(
                product_id,
                name=data["name"],
                description=data.get("description", ""),
                price=str(data["price"]),
                billing_interval=data["billing_interval"],
            )
            if error:
                return Response({"error": error}, status=400)
            return Response(result, status=201)
        return Response(serializer.errors, status=400)


# subscriptions/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import requests
from plans.models import Plan
from paypal_auth import get_paypal_access_token


class UpdatePlanPriceView(APIView):
    def post(self, request):
        plan_id = request.data.get("paypal_plan_id")
        new_price = request.data.get("price")

        if not plan_id or not new_price:
            return Response({"error": "Missing plan_id or price"}, status=400)

        try:
            plan = Plan.objects.get(paypal_plan_id=plan_id)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=404)

        # Get PayPal access token
        access_token = get_paypal_access_token()
        base_url = settings.PAYPAL_BASE_URL

        url = f"{base_url}/v1/billing/plans/{plan_id}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        patch_data = [
            {
                "op": "replace",
                "path": "/billing_cycles/@reference_id=='REGULAR'/pricing_scheme/fixed_price",
                "value": {"currency_code": "USD", "value": str(new_price)},
            }
        ]

        response = requests.patch(url, json=patch_data, headers=headers)

        if response.status_code == 204:
            User.objects.filter(paypal_plan_id=plan_id).update(is_subscribed=False)
            plan.price = new_price
            plan.save()
            return Response({"success": "Plan price updated successfully"})
        else:
            return Response(
                {"error": "PayPal API error", "paypal_response": response.json()},
                status=response.status_code,
            )
