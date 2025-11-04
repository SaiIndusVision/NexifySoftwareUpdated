import os
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.views.static import serve as static_serve

BASE_DIR = settings.BASE_DIR
schema_view = get_schema_view(
    openapi.Info(
        title="Anamoly Tool",
        default_version='v1',
        description="These are the APIs used for building the Anamoly Tool.",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="sai@indusvision.ai"),
        license=openapi.License(name="Awesome License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/refresh_token/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('users.urls')),
    path('api/', include('workspace.urls')),
    path('api/', include('sku.urls')),
    path('api/', include('image_modifier_app.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # path('', include('django_prometheus.urls')),
]

# Serve React frontend assets
urlpatterns += [
    re_path(r'^assets/(?P<path>.*)$', static_serve, {
        'document_root': os.path.join(BASE_DIR, 'frontend', 'dist', 'assets'),
    }),
    
    # React frontend fallback route - Make sure this stays at the end
    re_path(r'^(?!assets/|media/).*$', TemplateView.as_view(template_name="index.html")),
]

# Add media serving for both development and production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns.insert(-1, re_path(r'^media/(?P<path>.*)$', static_serve, {
        'document_root': settings.MEDIA_ROOT,
    }))