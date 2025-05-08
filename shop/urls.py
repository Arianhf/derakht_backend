# shop/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from wagtail.api.v2.router import WagtailAPIRouter

from .views.product import (
    ProductViewSet,
    CategoryViewSet,
    ProductInfoPageAPIViewSet,
)
from .views.cart import CartViewSet
from .views.order import OrderViewSet
from .views.payment import (
    PaymentRequestView,
    PaymentCallbackView,
    PaymentStatusView,
    PaymentMethodsView,
    PaymentVerificationView,
)


app_name = "shop"

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="order")

wagtail_api_router = WagtailAPIRouter("shop")
wagtail_api_router.register_endpoint("product-info", ProductInfoPageAPIViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path(
        "payments/request/<uuid:order_id>/",
        PaymentRequestView.as_view(),
        name="request_payment",
    ),
    path(
        "payments/verify/",
        PaymentVerificationView.as_view(),
        name="verify_payment_frontend",
    ),
    path(
        "payments/callback/<str:gateway>/<uuid:payment_id>/",
        PaymentCallbackView.as_view(),
        name="payment_callback",
    ),
    path(
        "payments/status/<uuid:payment_id>/",
        PaymentStatusView.as_view(),
        name="payment_status",
    ),
    path("payments/methods/", PaymentMethodsView.as_view(), name="payment_methods"),
]
