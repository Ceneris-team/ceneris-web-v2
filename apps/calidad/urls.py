# calidad/urls.py

from django.urls import path
from . import views
from recursoshumanos import views as recursoshumanos_views

app_name = 'calidad'


urlpatterns = [
    path('main/', views.gestion_calidad, name='gestion_calidad'),
    # Nueva ruta para el dashboard de estadísticas
    path('', views.estadisticas_calidad, name='estadisticas_calidad'),
    
    # APIs para los modales del dashboard
    path('api/trabajadores-vigentes/', views.api_trabajadores_vigentes, name='api_trabajadores_vigentes'),
    path('api/trabajadores-vencidos/', views.api_trabajadores_vencidos, name='api_trabajadores_vencidos'),
    path('api/emos-programados/', views.api_emos_programados, name='api_emos_programados'),
    path('api/trabajadores-sin-emo/', views.api_trabajadores_sin_emo, name='api_trabajadores_sin_emo'),
    
    # Rutas para Trabajadores
    path('emos/crear/', views.crear_emo, name='crear_emo'),
    path('eliminar-emo/<int:emo_id>/', views.eliminar_emo, name='eliminar_emo'),
    path('filtro/', views.filtro_trabajador, name='filtro'),

    path('programar-emo/', views.programar_emo, name='programar_emo'),
    path('preview-emo-email/', views.preview_emo_email, name='preview_emo_email'),
    path('emos/<int:emo_id>/preview-correo-edicion/', views.preview_correo_edicion_emo, name='preview_correo_edicion_emo'),
    path('info-trabajador/', views.buscar_trabajador_info, name='buscar_trabajador_info'),
    path('emos/pendientes/', views.lista_emos_pendientes, name='lista_emos_pendientes'),
    path('get-subproyectos/', views.get_subproyectos_ajax, name='get_subproyectos_ajax'),
    path('emos/vigentes/', views.lista_emos_vigentes, name='lista_emos_vigentes'),
    path('trabajadores/aptos/', views.lista_aptos_con_restriccion, name='lista_aptos_con_restriccion'),

    # Nueva ruta para registrar resultados, que acepta un ID
    path('emos/<int:emo_id>/registrar-resultado/', views.registrar_resultado_emo, name='registrar_resultado_emo'),
    path('emos/<int:emo_id>/editar/', views.editar_emo, name='editar_emo'),
    path('emos/<int:emo_id>/editar-programado/', views.editar_emo_programado, name='editar_emo_programado'),

    # Nuevas rutas para los listados
    path('emos/por-vencer/', views.lista_emos_por_vencer, name='lista_emos_por_vencer'),
    path('emos/vencidos/', views.lista_emos_vencidos, name='lista_emos_vencidos'),
    # Nueva ruta para eliminar, que acepta un ID
    path('emos/<int:emo_id>/eliminar/', views.eliminar_emo_pendiente, name='eliminar_emo_pendiente'),

    #enlaces de filtro
    path('emos/', views.lista_emos, name='lista_emos'),
    path('reporte-aptitud/', views.reporte_aptitud_emos, name='reporte_aptitud_emos'),
    path('reporte-emos/', views.reporte_maestro_emos, name='reporte_maestro_emos'),

    # --- ¡NUEVA RUTA PARA EDITAR! ---
    # Captura el DNI del trabajador desde la URL
    #path('trabajadores/<str:dni>/editar/', views.editar_trabajador, name='editar_trabajador'),


    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/crear/', views.crear_empresa, name='crear_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),

    #path('programacion/', views.lista_programacion_emos, name='lista_programacion_emos'),

    path('por-confirmar/', views.lista_emos_por_confirmar, name='lista_emos_por_confirmar'),
    path('emos/<int:emo_id>/confirmar/', views.confirmar_lectura_emo, name='confirmar_lectura_emo'),

    # rutas para subsanacion de EMos 
    path('emos/<int:emo_id>/subir-subsana/', views.subir_subsana_emo, name='subir_subsana_emo'),
    path('emos/<int:emo_id>/validar-subsana/', views.validar_subsana_emo, name='validar_subsana_emo'),
    # gestionar las vistas para gestion de proyectos
    # direcciona para lista subsanacion
    path('para-subsanar/', views.lista_para_subsanar, name='lista_para_subsanar'),
    path('emos/<int:emo_id>/rechazar-subsana/', views.rechazar_subsana_emo, name='rechazar_subsana_emo'),
    # direccion para dashboard de gestion de lectura
    path('lecturas/', views.gestion_lecturas, name='gestion_lecturas'),
    # Esta es la página principal para la sección de Observaciones
    path('observaciones/', views.lista_observaciones, name='lista_observaciones'),
    # rutas para controles
    path('controles/<int:control_id>/registrar/', views.registrar_control, name='registrar_control'),
    # --- ¡NUEVA RUTA para el dashboard de tarjetas de clínicas! ---
    path('clinicas-gestion/', views.gestion_clinicas, name='gestion_clinicas'),
    # --- ¡NUEVAS RUTAS PARA LA GESTIÓN DE CLÍNICAS! ---
    path('clinicas/', views.lista_clinicas, name='lista_clinicas'),
    path('clinicas/crear/', views.crear_clinica, name='crear_clinica'),
    path('clinicas/<int:pk>/editar/', views.editar_clinica, name='editar_clinica'),
    path('clinicas/<int:pk>/eliminar/', views.eliminar_clinica, name='eliminar_clinica'),
    # --- nuevas rutas para gestion de cargos ---

    path('tasks/trigger-daily-report/', views.trigger_daily_report, name='trigger_daily_report'),
    path('exportar-reportes/', views.pagina_exportar_reportes, name='pagina_exportar_reportes'),

    path('emo/<int:emo_id>/gestion/', views.seleccionar_edicion_emo, name='seleccionar_edicion_emo'),

    path('emo/<int:emo_id>/documentos/', views.ver_documentos_emo, name='ver_documentos_emo'),
    path('emo/<int:emo_id>/eliminar/', views.eliminar_emo, name='eliminar_emo'),

    # Ruta para trabajadores
    path('trabajadores/', views.gestion_empleados, name='gestion_empleados'),
    path('trabajadores/lista/', views.lista_trabajadores, name='lista_trabajadores'),
    path('trabajadores/jefaturas/', views.gestionar_jefaturas, name='gestionar_jefaturas'),
    path('trabajadores/sedes/', views.gestionar_sedes_trabajadores, name='gestionar_sedes_trabajadores'),

    # Ruta para observaciones
    path('gestion_observaciones/', views.gestion_observaciones, name='gestion_observaciones'),
    path('observaciones/lista/', views.lista_observaciones, name='lista_observaciones'),
    path('controles/lista/', views.lista_controles, name='lista_controles'),
    path('observaciones/hub/', views.hub_observaciones, name='hub_observaciones'),
]