# users/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserView, AddressViewSet, AuthView, ProfileImageView

from .views import (
    CustomTokenObtainPairView,
    SignUpView,
    verify_email,
    request_password_reset,
    reset_password,
)

router = DefaultRouter()
router.register(r"addresses", AddressViewSet, basename="address")


urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-email/", verify_email, name="verify-email"),
    path(
        "request-password-reset/", request_password_reset, name="request-password-reset"
    ),
    path("reset-password/", reset_password, name="reset-password"),
    path("", include(router.urls)),
    path("me/", UserView.as_view(), name="user-profile"),
    path("me/profile-image/", ProfileImageView.as_view(), name="profile-image"),
    path(
        "addresses/<str:pk>/set_default/",
        AddressViewSet.as_view({"post": "set_default"}),
        name="address-set-default",
    ),
]


# urlpatterns = [
#     path('login/', AuthView.as_view({'post': 'login'}), name='user-login'),
#     path('signup/', AuthView.as_view({'post': 'signup'}), name='user-signup'),
#     path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
# ]
