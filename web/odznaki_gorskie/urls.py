# odznaki_gorskie/urls.py

"""
URL configuration for odznaki_gorskie project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Jawnie wskazujemy Django, których funkcji ma użyć do obsługi błędów.
handler404 = 'odznaki.views.error_views.handler404'
handler500 = 'odznaki.views.error_views.handler500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('silk/', include('silk.urls', namespace='silk')),
    path('', include(('odznaki.urls', 'odznaki'), namespace='odznaki')),
]

if settings.DEBUG:
    # Dołączamy debug_toolbar
    urlpatterns += [
       path('__debug__/', include('debug_toolbar.urls')),
    ]
    
    # POPRAWKA: Dodajemy jawne serwowanie zarówno plików MEDIA, jak i STATIC
    # To jest standardowa i zalecana konfiguracja dla środowiska deweloperskiego.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)