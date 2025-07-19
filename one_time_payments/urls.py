from .views import CreateOrderView, CaptureOrderView
from django.urls import path, include
from .views import CheckOrderStatusView


urlpatterns = [
    path("create-order/", CreateOrderView.as_view(), name="create-order"),
    path("capture-order/", CaptureOrderView.as_view(), name="capture-order"),
    path("check-order/", CheckOrderStatusView.as_view(), name="check-order-status"),
]
