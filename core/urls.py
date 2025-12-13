# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('feature-flags/', views.feature_flags, name='feature-flags'),
    path('feature-flags/<str:name>/', views.feature_flag_detail, name='feature-flag-detail'),
    path('search/', views.global_search, name='global-search'),
    # Generic comment endpoints
    path('comments/<str:app_label>/<str:model_name>/<str:identifier>/', views.comments_list_create, name='comments-list-create'),
    path('comments/<uuid:comment_id>/', views.comment_delete, name='comment-delete'),
]