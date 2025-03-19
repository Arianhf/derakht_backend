# shop/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api.views import OrderViewSet, PaymentViewSet, CartViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'products', ProductViewSet, basename='product')

app_name = 'shop'

urlpatterns = [
    path('', include(router.urls)),
]