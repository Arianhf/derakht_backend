# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('feature-flags/', views.feature_flags, name='feature-flags'),
    path('feature-flags/<str:name>/', views.feature_flag_detail, name='feature-flag-detail'),
    path('search/', views.global_search, name='global-search'),
]