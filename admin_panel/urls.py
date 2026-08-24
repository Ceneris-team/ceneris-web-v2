"""
URL configuration for admin_panel project.

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
# admin_panel/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# --- Importaciones de Vistas ---
# Un solo bloque para importar todo lo que necesitas de cada app

# Vistas de la app de recursos humanos
from recursoshumanos.views import CustomLoginView

urlpatterns = [
    path('api/', include('api.urls')),
    path('seguridad/', include('accesos.urls')),
    
    # --- RUTAS DE AUTENTICACIÓN WEB ---
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # Panel de administración de Django
    path('admin/', admin.site.urls),

    # URLs de la aplicación de recursos humanos
    path('recursoshumanos/', include('recursoshumanos.urls', namespace='recursoshumanos')),

    # URLs de la aplicación de calidad
    path('calidad/', include('calidad.urls', namespace='calidad')),

    # Redirección de la raíz al login
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),

    path('administracion/', include('administracion.urls', namespace='administracion')),

    path('cotizaciones/', include('cotizaciones.urls', namespace='cotizaciones')),

    path('gases/', include('cenerisapp.urls', namespace='cenerisapp')),

    path('proyectos/', include('proyectos.urls', namespace='proyectos')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('personal/', include('personal.urls', namespace='personal')),
    path('metricas_ceneris/', include('metricas_ceneris.urls', namespace='metricas_ceneris')),
    path('notificaciones/', include('notificaciones.urls', namespace='notificaciones')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    