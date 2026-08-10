from django.urls import path
from . import views

app_name = 'cotizaciones'

urlpatterns = [
    path('editar/<int:pk>/', views.editar_cotizacion, name='editar_cotizacion'),
    path('dashboard/', views.dashboard_cotizaciones, name='dashboard_cotizaciones'),
    path('procesos/', views.lista_procesos, name='lista_procesos'),
    path('procesos/agendar/', views.agendar_cita, name='agendar_cita'),
    path('procesos/<int:pk>/', views.detalle_proceso, name='detalle_proceso'),
    path('procesos/<int:proceso_pk>/crear-cotizacion/', views.crear_cotizacion, name='crear_cotizacion'),
    path('auditoria/', views.dashboard_auditoria, name='dashboard_auditoria'),
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('api/check-ruc/', views.check_ruc_view, name='check_ruc_api'),
    path('proceso/<int:proceso_pk>/reasignar/', views.reasignar_proceso_view, name='reasignar_proceso'),
    path('cotizacion/<int:cotizacion_pk>/editar/', views.editar_cotizacion, name='editar_cotizacion'),
    path('empresas/', views.gestion_empresas, name='gestion_empresas'),
    path('empresas/lista/', views.lista_empresas_central, name='lista_empresas_central'),
    # 2. El formulario para registrar una nueva empresa
    path('empresas/registrar/', views.registrar_empresa, name='registrar_empresa'),
    path('empresas/gestion/', views.centro_gestion_empresas, name='centro_gestion_empresas'),
]