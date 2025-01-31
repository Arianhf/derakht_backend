from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView, SignUpView, verify_email,
    request_password_reset, reset_password
)

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/', verify_email, name='verify-email'),
    path('request-password-reset/', request_password_reset, name='request-password-reset'),
    path('reset-password/', reset_password, name='reset-password'),
]
