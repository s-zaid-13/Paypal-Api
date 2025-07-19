from django.urls import path
from .views import AllUsersWithSubscriptionView

urlpatterns = [
    path("users/", AllUsersWithSubscriptionView.as_view(), name="all-users"),
]
