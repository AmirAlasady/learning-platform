# In learning_platform/urls.py - modify the URL patterns

from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from .views import protected_media_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),  # Template-based auth
    
    path('api/v1/auth/', include('accounts.api_urls')),  # API-based auth

    # apps
    path('', include('courses.urls')),
    path('subscribtion/', include('subscribtion.urls')),
    
    # Replace the standard static media URL with our protected view
    re_path(r'^media/(?P<path>.*)$', protected_media_view, name='protected_media'),
]

# Comment out this line to prevent direct media access
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)