from django.urls import include, path
from .api_views import (
    PasswordResetView,
    UserProfileView,
    EmailChangeView,
    UsernameChangeView,
    NameChangeView,
    ProfilePhotoUploadView,
)

urlpatterns = [
    # Djoser endpoints
    path('', include('djoser.urls')),
    path('', include('djoser.urls.jwt')),

    # Custom API endpoints
    path('profile/', UserProfileView.as_view(), name='api-profile'),
    path('change-email/', EmailChangeView.as_view(), name='api-change-email'),
    path('change-username/', UsernameChangeView.as_view(), name='api-change-username'),
    path('change-name/', NameChangeView.as_view(), name='api-change-name'),
    path('upload-profile-photo/', ProfilePhotoUploadView.as_view(), name='api-upload-profile-photo'),
    path('reset-pass/', PasswordResetView.as_view(), name='api-reset-password')
]
