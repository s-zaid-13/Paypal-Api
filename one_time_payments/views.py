from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import create_paypal_order, capture_paypal_order, get_paypal_order_details
from .serializers import CreateOrderSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest


class CreateOrderView(APIView):
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if serializer.is_valid():
            items_data = [dict(item) for item in serializer.validated_data["items"]]
            currency = serializer.validated_data["currency"]
            try:
                result, error = create_paypal_order(request.user, items_data, currency)
                if error:
                    return Response({"error": error}, status=400)
                return Response(result, status=201)
            except Exception as error:
                return Response({"error": str(error)}, status=500)

        return Response(serializer.errors, status=400)


class CaptureOrderView(APIView):
    def post(self, request):
        user = request.user
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "Missing order_id"}, status=400)

        try:
            result = capture_paypal_order(user, order_id)
            if "error" in result:
                return Response(
                    {"error": result["error"], "details": result["details"]}, status=400
                )
            return Response({"message": "Payment captured", "details": result})

        except ValidationError as error:
            return Response({"error": error.detail[0]}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)


class CheckOrderStatusView(APIView):
    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "Missing order_id"}, status=400)

        result = get_paypal_order_details(order_id)
        return Response(result)


@login_required
def one_time_success(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Missing order ID")
    return render(request, "one_time_success.html")


@login_required
def one_time_cancel(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Missing order ID")
    return render(request, "one_time_cancel.html")
