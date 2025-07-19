from django.urls import path
from .views import PlanListView, CreatePayPalPlanView, UpdatePlanPriceView

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("create-plan/", CreatePayPalPlanView.as_view(), name="create-plan"),
    path("update-plan/", UpdatePlanPriceView.as_view(), name="create-plan"),
]
