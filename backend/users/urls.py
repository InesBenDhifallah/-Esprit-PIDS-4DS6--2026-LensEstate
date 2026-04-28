from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView,
    PasswordResetRequestView, PasswordResetConfirmView,
    ProfileView, FavoriteListView, FavoriteDeleteView,
    SavedSearchListView, GoogleLoginView,
)

urlpatterns = [
    path('auth/register/',               RegisterView.as_view()),
    path('auth/login/',                  LoginView.as_view()),
    path('auth/logout/',                 LogoutView.as_view()),
    path('auth/refresh/',                TokenRefreshView.as_view()),
    path('auth/password-reset/',         PasswordResetRequestView.as_view()),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('auth/google/',                 GoogleLoginView.as_view()),
    path('users/me/',                    ProfileView.as_view()),
    path('users/favorites/',             FavoriteListView.as_view()),
    path('users/favorites/<int:pk>/',    FavoriteDeleteView.as_view()),
    path('users/saved-searches/',        SavedSearchListView.as_view()),
]