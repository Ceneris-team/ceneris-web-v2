# mi_app/urls.py
from django.urls import path
from . import views

app_name = 'metricas_ceneris'

urlpatterns = [
    path('', views.inicio_inteligente, name='inicio_metricas'),
    path('panel/', views.panel_jefe, name='panel_jefe'),
    path('dashboard-jefe/', views.dashboard_jefe, name='dashboard_jefe'),
    path('responsable/dashboard/', views.dashboard_responsable, name='dashboard_responsable'),
    path('responsable/evaluaciones/', views.panel_responsable, name='panel_responsable'),
    path('responsable/asistencias/', views.panel_asistencias, name='panel_asistencias_responsable'),
    path('mi-dashboard/', views.dashboard_trabajador, name='dashboard_trabajador_legacy'),
    path('trabajador/mi-dashboard/', views.dashboard_trabajador, name='dashboard_trabajador'),
    path('evaluar/<int:trabajador_id>/<str:tipo>/', views.evaluar_trabajador, name='evaluar_trabajador'),
    path('evaluar/corregir/<int:evaluacion_id>/', views.corregir_evaluacion, name='corregir_evaluacion'),
    path('historial/<int:trabajador_id>/', views.historial_trabajador, name='historial_trabajador'),
    path('panel_jefe/', views.panel_jefe, name='panel_jefe'),
    path('mis-evaluaciones/', views.mis_evaluaciones, name='mis_evaluaciones'), 
    path('detalle/<int:evaluacion_id>/', views.detalle_evaluacion, name='detalle_evaluacion'),
    path('asistencias/', views.panel_asistencias, name='panel_asistencias'),
    path('gerencia/', views.dashboard_gerente, name='dashboard_gerente'),
    path('gerencia/ranking-general/', views.ranking_general, name='ranking_general'),
    path('gerencia/evaluar-jefaturas/', views.panel_evaluacion_gerente, name='panel_evaluacion_gerente'),
    path('gerencia/areas-directas/<int:area_id>/', views.panel_area_directa_gerencia, name='panel_area_directa_gerencia'),
    path('gerencia/asistencias/', views.panel_asistencias, name='panel_asistencias_gerente'),
    path('gerencia/importar-asistencias/', views.importar_asistencias, name='importar_asistencias'),
    
    # AJAX endpoints
    path('ajax/datos-ranking/', views.ajax_datos_ranking, name='ajax_datos_ranking'),
    path('ajax/datos-grafico-areas/', views.ajax_datos_grafico_areas, name='ajax_datos_grafico_areas'),
    path('ajax/datos-podio/', views.ajax_datos_podio, name='ajax_datos_podio'),
    path('ajax/datos-area-lider/', views.ajax_datos_area_lider, name='ajax_datos_area_lider'),
    
    # Exportación endpoints
    path('exportacion/', views.exportacion_metricas_view, name='exportacion_metricas'),
    path('exportacion/rrhh/', views.exportacion_metricas_rrhh_view, name='exportacion_metricas_rrhh'),
    path('exportar/ranking/', views.exportar_ranking_excel, name='exportar_ranking_excel'),
    path('exportar/mi-area/', views.exportar_ranking_excel_area, name='exportar_ranking_excel_area'),
]