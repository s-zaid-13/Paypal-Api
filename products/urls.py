from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.include_root_view = False

urlpatterns = [
    path("", include(router.urls)),
]
