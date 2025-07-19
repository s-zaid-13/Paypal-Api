"""
URL configuration for paypal_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from .utils import schema_view
from one_time_payments.views import one_time_success, one_time_cancel
from subscriptions.views import subscription_success, subscription_cancel

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("products.urls")),
    path("api/", include("transactions.urls")),
    path("api/", include("one_time_payments.urls")),
    path("api/", include("plans.urls")),
    path("api/", include("subscriptions.urls")),
    path("webhooks/", include("webhooks.urls")),
    path(
        "api/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path("payment/success/", one_time_success, name="one_time_success"),
    path("payment/cancel/", one_time_cancel, name="one_time_cancel"),
    path("subscription/success/", subscription_success, name="subscription_success"),
    path("subscription/cancel/", subscription_cancel, name="subscription_cancel"),
]
