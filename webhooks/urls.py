from django.urls import path
from .views import paypal_webhook_view

urlpatterns = [
    path("paypal/", paypal_webhook_view, name="paypal-webhook"),
]
