# gestion_consumo/urls.py

from django.urls import path
from . import views
from .views import (
    gestionar_requerimientos,
    lista_requerimientos,
    RequerimientoUpdateView,
    RequerimientoDeleteView,
    registrar_avance,
    RegistroConsumoUpdateView,
    RegistroConsumoDeleteView,
    reporte_avance_mensual,
    reporte_avance_anual,
    dashboard_estadistico,
    lista_requerimientos_criticos,
)

app_name = 'administracion' # Namespace para evitar conflictos de nombres de URL

urlpatterns = [
    # URL para la Pantalla 1: Crear un nuevo requerimiento
    path('requerimiento/nuevo/', gestionar_requerimientos, name='crear_requerimiento'),

    # Si más adelante implementas una vista basada en clases para editar,
    # descomenta y ajusta la siguiente línea importando la clase arriba.
    # path('requerimiento/<int:pk>/editar/', RequerimientoUpdateView.as_view(), name='editar_requerimiento'),
    # Pantalla 2: Lista de consulta de requerimientos
    path('requerimientos/lista/', lista_requerimientos, name='lista_requerimientos'),

    # Rutas para los botones de la tabla
    path('requerimiento/<int:pk>/editar/', RequerimientoUpdateView.as_view(), name='editar_requerimiento'),
    path('requerimiento/<int:pk>/eliminar/', RequerimientoDeleteView.as_view(), name='eliminar_requerimiento'),
    # Próximamente: añadiremos aquí las URLs para las pantallas 2, 3, 4 y 5

    path('requerimiento/<int:requerimiento_id>/registrar/', registrar_avance, name='registrar_avance'),

    path('registro/<int:pk>/editar/', RegistroConsumoUpdateView.as_view(), name='editar_registro'),
    path('registro/<int:pk>/eliminar/', RegistroConsumoDeleteView.as_view(), name='eliminar_registro'),

    path('reportes/avance-mensual/', reporte_avance_mensual, name='reporte_mensual'),

    path('reportes/avance-anual/', reporte_avance_anual, name='reporte_anual'),

    path('dashboard/', dashboard_estadistico, name='dashboard_estadistico'),
    path('requerimientos/criticos/', lista_requerimientos_criticos, name='lista_requerimientos_criticos'),

    path('agentes/', views.AgenteListView.as_view(), name='lista_agentes'),
    path('agentes/nuevo/', views.AgenteCreateView.as_view(), name='crear_agente'),
    path('agentes/editar/<int:pk>/', views.AgenteUpdateView.as_view(), name='editar_agente'),
    path('agentes/eliminar/<int:pk>/', views.AgenteDeleteView.as_view(), name='eliminar_agente'),
    path('reportes/facturacion/', views.reporte_facturacion, name='reporte_facturacion'),
]