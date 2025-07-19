from django.urls import path
from .views import (
    CreateSubscriptionView,
    CancelPendingSubscriptionView,
    CancelSubscriptionView,
    RefundPaymentView,
    ShiftSubscriptionView,
    ReactivateSubscriptionView,
    PauseSubscriptionView,
    ReviseSubscriptionView,
)

urlpatterns = [
    path(
        "create-subscription/",
        CreateSubscriptionView.as_view(),
        name="create-subscription",
    ),
    path(
        "cancel-pending-subscription/",
        CancelPendingSubscriptionView.as_view(),
        name="cancel-pending-subscription",
    ),
    path(
        "cancel-subscription/",
        CancelSubscriptionView.as_view(),
        name="cancel-subscription",
    ),
    # urls.py
    path("refund-payment/", RefundPaymentView.as_view(), name="refund-payment"),
    path(
        "shift-subscription/",
        ShiftSubscriptionView.as_view(),
        name="shift-subscription",
    ),
    path(
        "pause-subscription/",
        PauseSubscriptionView.as_view(),
        name="pause-subscription",
    ),
    path(
        "reactivate-subscription/",
        ReactivateSubscriptionView.as_view(),
        name="reactivate-subscription",
    ),
    path(
        "revise-subscription/",
        ReviseSubscriptionView.as_view(),
        name="revise-subscription",
    ),
]
