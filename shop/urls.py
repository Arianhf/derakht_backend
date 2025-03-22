# shop/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.product import ProductViewSet, CategoryViewSet
from .views.cart import CartViewSet
from .views.order import OrderViewSet

app_name = "shop"

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
]
