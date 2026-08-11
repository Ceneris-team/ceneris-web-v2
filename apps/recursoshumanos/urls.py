# recursoshumanos/urls.py
from django.contrib import admin
from django.urls import include, path
from . import views
from recursoshumanos.views import reporte_faltas_web
from . import api_views

app_name = 'recursoshumanos'


urlpatterns = [

    # --- DASHBOARD Y REPORTES ---
    path('', views.estadisticas_general, name='dashboard'),
    path('consulta-asistencias/', views.consulta_asistencias_view, name='consulta_asistencias'),
    path('consulta-asistencias/', views.consulta_asistencias_view, name='lista_consulta'),
    
    # --- TRABAJADOR FRAUDELENTO ---
    path('fraude/', views.reportes_fraude_view, name='reportes_fraude'), # <-- AÑADE ESTA LÍNEA
    
    # --- CALENDARIO ---
    path('reporte-mensual/', views.reporte_mensual, name='reporte_mensual'),
    
    # --- REPORTES EXCEL ASISTENCIA ---
    path('reportes/', views.gestion_reporte_maestro, name='gestion_reportes'),
    path('reportes/justificaciones/', views.reporte_justificaciones_rrhh, name='reporte_justificaciones_rrhh'),
    path('exportar-diario/', views.exportar_reporte_diario, name='exportar_reporte_diario'),
    path('exportar-semanal/', views.exportar_reporte_semanal, name='exportar_reporte_semanal'),
    path('exportar-planilla/', views.exportar_formato_planilla, name='exportar_formato_planilla'),
    path('exportar-maestro/', views.exportar_reporte_maestro, name='exportar_reporte_maestro'),
    
    # --- DETALLES TRABAJADOR ---
    path('trabajador/<str:dni>/', views.trabajador_detail_view, name='trabajador_detail'),

    # --- ¡NUEVAS RUTAS PARA la gestion de HORARIOS! ---
    path('horarios/', views.gestion_horarios, name='gestion_horarios'),

    # --- HU-06 (CAV-15): TOLERANCIA DE HORARIO ---
    path('tolerancia/', views.gestion_tolerancia, name='gestion_tolerancia'),
    path('api/tolerancia/', api_views.ConfiguracionToleranciaListCreateView.as_view(), name='api_tolerancia_list_create'),
    path('api/tolerancia/<int:pk>/', api_views.ConfiguracionToleranciaDetailView.as_view(), name='api_tolerancia_detail'),

    # --- ¡NUEVAS RUTAS PARA la gestion de Ubicaciones! ---
    path('ubicaciones/', views.gestion_ubicaciones, name='gestion_ubicaciones'),
    path('ubicaciones/lista/', views.lista_ubicaciones, name='lista_ubicaciones'),
    path('ubicaciones/crear/', views.ubicacion_crear, name='ubicacion_crear'),
    path('empleados/<str:dni>/asignar-ubicaciones/', views.asignar_ubicaciones_trabajador, name='asignar_ubicaciones_trabajador'),
    path('empleados/<str:dni>/actualizar-ubicaciones/', views.actualizar_ubicaciones_trabajador, name='actualizar_ubicaciones_trabajador'),
    path('ubicaciones/editar/<int:pk>/', views.ubicacion_editar, name='ubicacion_editar'),
    path('ubicaciones/eliminar/<int:pk>/', views.ubicacion_eliminar, name='ubicacion_eliminar'),
    path('asignacion-ubicaciones/', views.asignacion_masiva_ubicaciones, name='asignacion_masiva_ubicaciones'),
    path('actualizar-asignacion-ubicacion/', views.actualizar_asignacion_ubicacion, name='actualizar_asignacion_ubicacion'),

    # /dashboard/justificacion/
    path('justificaciones/', views.gestion_justificaciones, name='gestion_justificaciones'),


    path('solicitudes/', views.gestion_solicitudes, name='gestion_solicitudes'),

    path('tareo/', views.gestion_tareo, name='gestion_tareo'),    
    # --- ¡NUEVAS RUTAS PARA la gestion de trabajadores! ---
    path('empleados/', views.gestion_empleados, name='gestion_empleados'),
    path('empleados/lista/', views.lista_trabajadores, name='lista_trabajadores'),
    path('empleados/crear/', views.crear_trabajador, name='crear_trabajador'),
    path('empleados/<int:pk>/editar/', views.editar_trabajador, name='editar_trabajador'),
    path('empleados/<int:pk>/info/', views.info_trabajador, name='info_trabajador'),
    path('empleados/<int:pk>/permisos/', views.gestionar_permisos, name='gestionar_permisos'),
    path('empleados/<int:pk>/permisos/', views.gestionar_permisos, name='gestionar_permisos_asistencia'),#por eliminar
    path('trabajadores/eliminar/<int:pk>/', views.eliminar_trabajador, name='eliminar_trabajador'),

    # --- ¡NUEVAS RUTAS PARA LA GESTIÓN DE EMPRESAS! ---
    path('empresas-gestion/', views.gestion_empresas, name='gestion_empresas'),
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/crear/', views.crear_empresa, name='crear_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),
    path('asignacion-empresas/', views.asignacion_masiva_empresas, name='asignacion_masiva_empresas'),
    path('actualizar-asignacion-empresa/', views.actualizar_asignacion_empresa, name='actualizar_asignacion_empresa'),

    # --- rutas para proyectos ---
    path('proyectos-gestion/', views.gestion_proyectos, name='gestion_proyectos'),
    path('proyectos/', views.lista_proyectos, name='lista_proyectos'),
    path('proyectos/crear/', views.crear_proyecto, name='crear_proyecto'),
    path('proyectos/<int:pk>/editar/', views.editar_proyecto, name='editar_proyecto'),
    path('proyectos/<int:pk>/eliminar/', views.eliminar_proyecto, name='eliminar_proyecto'),
    path('asignacion-proyectos/', views.asignacion_masiva_proyectos, name='asignacion_masiva_proyectos'),
    path('actualizar-asignacion-proyecto/', views.actualizar_asignacion_proyecto, name='actualizar_asignacion_proyecto'),


    # --- RUTAS CARGOS ---
    path('cargos-gestion/', views.gestion_cargos, name='gestion_cargos'),
    path('cargos/', views.lista_cargos, name='lista_cargos'),
    path('cargos/crear/', views.crear_cargo, name='crear_cargo'),
    path('cargos/<int:pk>/editar/', views.editar_cargo, name='editar_cargo'),
    path('cargos/<int:pk>/eliminar/', views.eliminar_cargo, name='eliminar_cargo'),
    path('asignacion-cargos/', views.asignacion_masiva_cargos, name='asignacion_masiva_cargos'),
    path('actualizar-asignacion-cargo/', views.actualizar_asignacion_cargo, name='actualizar_asignacion_cargo'),

    # --- RUTAS CENTRO DE COSTO ---
    path('centro-costo-gestion/', views.gestion_centro_costo, name='gestion_centro_costo'),
    path('centro-costo/', views.lista_centro_costo, name='lista_centro_costo'),
    path('centro-costo/crear/', views.crear_centro_costo, name='crear_centro_costo'),
    path('centro-costo/<int:pk>/editar/', views.editar_centro_costo, name='editar_centro_costo'),
    path('centro-costo/<int:pk>/eliminar/', views.eliminar_centro_costo, name='eliminar_centro_costo'),
    path('centro-costo/<int:pk>/trabajadores/', views.trabajadores_por_centro_costo, name='trabajadores_por_centro_costo'),
    path('asignacion-masiva/', views.asignar_trabajadores_centro_costo, name='asignacion_masiva_centro_costo'),
    path('actualizar-asignacion/', views.actualizar_asignacion_trabajador, name='actualizar_asignacion_trabajador'),

    # --- RUTAS DE ÁREAS ---
    path('areas/', views.gestion_areas, name='gestion_areas'),
    path('areas/lista/', views.lista_areas, name='lista_areas'),
    path('areas/crear/', views.crear_editar_area, name='crear_area'),
    path('areas/editar/<int:pk>/', views.crear_editar_area, name='editar_area'),
    path('areas/eliminar/<int:pk>/', views.eliminar_area, name='eliminar_area'),

    # --- RUTAS DISPOSITIVOS ---
    path('dispositivos/panel/', views.gestion_dispositivos_panel, name='gestion_dispositivos_panel'),
    path('dispositivos/asignacion/', views.gestion_dispositivos, name='gestion_dispositivos'),
    path('dispositivos/lista/', views.lista_dispositivos, name='lista_dispositivos'),
    path('dispositivos/crear/', views.crear_dispositivo, name='crear_dispositivo'),
    path('dispositivos/editar/<str:pk>/', views.editar_dispositivo, name='editar_dispositivo'),
    path('dispositivos/eliminar/<str:pk>/', views.eliminar_dispositivo, name='eliminar_dispositivo'),
    path('dispositivos/gestion/', views.gestion_dispositivos, name='gestion_dispositivos'),
    path('dispositivos/actualizar-asignacion/', views.actualizar_asignacion_dispositivo, name='actualizar_asignacion_dispositivo'),
    path('dispositivos/renombrar/', views.renombrar_dispositivo, name='renombrar_dispositivo'),
    
    # --- HORAS EXTRA ---
    path('horas-extra/panel-aprobacion/', views.panel_aprobacion_horas_extra, name='panel_aprobacion_he'),
    path('horas-extra/procesar/<int:solicitud_id>/<str:accion>/', views.procesar_solicitud_horas_extra, name='procesar_solicitud_he'),
    path('recursoshumanos/reportes/faltas/', reporte_faltas_web, name='reporte_faltas_web'),
]