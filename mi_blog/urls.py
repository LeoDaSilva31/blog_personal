from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),
    path('landingpage/', include('landingpage.urls')),
    path('propiedades/', include('propiedades.urls', namespace='propiedades')),
]

# Servir MEDIA para el demo (dev y prod en Render)
if settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
