from django.urls import path
from . import views

app_name = 'cenerisapp'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('dashboard/', views.dashboard_index, name='home'),
    path('registro/', views.register, name='registro'),
    path('dispositivos/', views.inventario_dispositivo, name='lista_dispositivos'),
    path('dispositivos/editar/<int:id_dispositivo>/', views.editar_dispositivo, name='editar_dispositivo'),
    path('dispositivos/eliminar/<int:id_dispositivo>/', views.eliminar_dispositivo, name='eliminar_dispositivo'),
    path('dispositivos/crear/', views.crear_dispositivo, name='crear_dispositivo'),
    path('dispositivos/<int:dispositivo_id>/asignar-sensores/<int:cantidad>/', 
        views.asignar_sensores_a_dispositivo, name='asignar_sensores_a_dispositivo'),
    path('dispositivos/<int:dispositivo_id>/asignar-partes/', 
        views.asignar_partes_a_dispositivo, name='asignar_partes_a_dispositivo'),
    path('dashboard/portatiles/', views.dashboard_portatiles, name='dashboard_portatiles'),
    path('garantias/', views.dashboard_garantias, name='dashboard_garantias'),
    path('reportes/fijos/', views.vista_reporte_fijos, name='vista_reporte_fijos'),
    path('flujo/', views.flujo, name='flujo_registro'), 
    path('registros/', views.lista_registros, name='lista_registros'), 
    path('registros/devolver/<int:registro_id>/', views.registrar_devolucion, name='registrar_devolucion'),
    path('api/empleado-info/<int:empleado_id>/', views.get_empleado_info, name='get_empleado_info'),
    path('inventario/nuevo/', views.crear_inventario_lote, name='crear_inventario_lote'),
    path('inventario/<int:lote_id>/añadir-componentes/', views.añadir_componentes_a_lote, name='añadir_componentes_a_lote'),
    path('lotes/', views.lista_inventario, name='lista_lotes'),
    path('inventario/stock/', views.vista_stock, name='vista_stock'),
    path('inventario/<int:lote_id>/componentes/', views.lista_componentes, name='lista_componentes'),
    path('componentes/', views.componentes_indice, name='componentes_indice'),
    path('componentes/sensores/', views.lista_sensores, name='lista_sensores'),
    path('dashboard/fijos/', views.dashboard_fijos, name='dashboard_fijos'),
    path('ocurrencias/', views.muro_ocurrencias, name='muro_ocurrencias'),
    path('ocurrencias/<int:ocurrencia_id>/borrar/', views.borrar_ocurrencia, name='borrar_ocurrencia'),
    path('registros/rapido/', views.registro_rapido_in_out, name='registro_rapido_in_out'),
    path('reportes/gestor/<str:tipo_reporte>/', views.gestor_reportes, name='gestor_reportes'),
    path('api/buscar-empresas/', views.buscar_empresas_api, name='buscar_empresas_api'),
    path('api/puntos-exactos/', views.buscar_puntos_exactos_api, name='buscar_puntos_exactos_api'),
    path('dispositivos/<int:dispositivo_id>/informes/seleccionar-sensor/', views.seleccionar_sensor_para_informe, name='seleccionar_sensor_para_informe'),

    #avance fabio 25-08
    path('componentes/otros/', views.lista_otros_componentes, name='lista_otros_componentes'),
    path('componentes/<int:id_componente>/', views.detalle_componente, name='detalle_componente'),
    #path('certificado/<int:id_empresa>/', views.certificado_detalle, name='detalle_certificado'),
    path('certificados/<int:certificado_id>/descargar/', views.descargar_certificado, name='descargar_certificado'),
    path('dispositivos/<int:dispositivo_id>/certificados/', views.lista_certificados_dispositivo, name='lista_certificados_dispositivo'),
    # URL para crear un certificado para un dispositivo
    path('componentes/<int:componente_id>/certificados/crear/', views.certificado_form, name='crear_certificado_componente'),
    
    # URL para crear certificado de un DISPOSITIVO COMPLETO (para portátiles)
    path('dispositivos/<int:dispositivo_id>/certificados/crear/', views.certificado_form, name='crear_certificado_dispositivo'),
    
    path('componentes/<int:id_componente>/modificaciones/', views.modificaciones_componente, name='modificaciones_componente'),

    path('mantenimiento/inoperativos/', views.vista_inoperativos, name='vista_inoperativos'),

    path('modificaciones/cargar-historial/', views.cargar_historial_modificaciones, name='cargar_historial_modificaciones'),

    path('certificados/lote/seleccionar-dispositivos/', views.seleccionar_dispositivos_lote, name='seleccionar_dispositivos_lote'),

    # URL para la acción de marcar como operativo
    # Ejemplo: /mantenimiento/marcar-operativo/dispositivo/5/
    path('mantenimiento/marcar-operativo/<str:tipo_item>/<int:item_id>/', views.marcar_operativo, name='marcar_operativo'),

    path('alarmas/seleccionar/', views.seleccionar_dispositivo_alarma, name='seleccionar_dispositivo_alarma'),
    path('alarmas/configurar/<int:dispositivo_id>/', views.configurar_alarma, name='configurar_alarma'),
    path('api/dispositivo-tipo/<int:dispositivo_id>/', views.get_dispositivo_tipo, name='get_dispositivo_tipo'),
    path('reportes/crear/', views.crear_reporte, name='crear_reporte'),
    path('reportes/', views.lista_reportes, name='lista_reportes'),
    path('reportes/<int:reporte_id>/editar/', views.editar_reporte, name='editar_reporte'),
    path('calibraciones/', views.gestion_calibraciones, name='gestion_calibraciones'),
    path('sensores/<int:sensor_id>/informes/crear/', views.crear_informe_calibracion, name='crear_informe_calibracion'),

    
    # La nueva URL de la acción
    path('calibraciones/registrar/<int:dispositivo_id>/', views.registrar_calibracion_ahora, name='registrar_calibracion_ahora'),
    path('ventas/', views.lista_ventas, name='lista_ventas'),
    path('ventas/crear/', views.crear_venta, name='crear_venta'),
    path('api/search-componentes-disponibles/', views.search_componentes_disponibles, name='search_componentes_disponibles'),
    path('ventas/<int:venta_id>/completar/', views.completar_venta, name='completar_venta'),
    path('modificaciones/', views.lista_modificaciones, name='lista_modificaciones'),
    path('modificaciones/crear/', views.crear_modificacion, name='crear_modificacion'),
    path('modificaciones/<int:modificacion_id>/editar/', views.editar_modificacion, name='editar_modificacion'),
    path('api/get-partes-y-sensores/', views.get_partes_y_sensores_por_dispositivo, name='api_get_partes_y_sensores'),
    path('tecnicos/', views.tecnicos_indice, name='tecnicos_indice'),
    path('tecnicos/lista_empresas/', views.lista_empresas, name='lista_empresas'),
    path('tecnicos/lista_areas/', views.lista_areas, name='lista_areas'),
    path('tecnicos/lista_empleados/', views.lista_empleados, name='lista_empleados'),
    path('empleados/crear/', views.crear_empleado, name='crear_empleado'),
    path('tecnicos/crear_empresa/', views.crear_empresa, name='crear_empresa'),
    path('tecnicos/editar_empresa/<int:empresa_id>/', views.editar_empresa, name='editar_empresa'),
    path('tecnicos/eliminar/<int:empresa_id>/', views.eliminar_empresa, name='eliminar_empresa'),
    path('tecnicos/crear_area/', views.crear_area, name='crear_area'),
    path('tecnicos/editar_area/<int:area_id>/', views.editar_area, name='editar_area'),
    path('tecnicos/eliminar_area/<int:area_id>/', views.eliminar_area, name='eliminar_area'),
    path('programas/', views.lista_programas, name='lista_programas'),
    path('programas/crear/', views.crear_programa, name='crear_programa'),
    path('programas/<int:programa_id>/editar/', views.editar_programa, name='editar_programa'),
    path('dispositivos/<int:dispositivo_id>/fotos/', views.gestionar_fotos_dispositivo, name='gestionar_fotos_dispositivo'),
    path('dispositivos/<int:dispositivo_id>/marcar-cardex/', views.marcar_cardex_revisado, name='marcar_cardex_revisado'),

    path('dispositivos/<int:dispositivo_id>/mantenimiento/crear/', views.crear_mantenimiento, name='crear_mantenimiento'),
    path('api/get-tipos-componentes/', views.get_tipos_componentes, name='api_get_tipos_componentes'),
    path('api/get-componentes-sin-ns/', views.get_componentes_sin_ns, name='api_get_componentes_sin_ns'),
    path('api/get-ns-por-tipo/', views.get_ns_por_tipo_api, name='api_get_ns_por_tipo'),
    path('api/get-puntos-por-area/', views.get_puntos_por_area_api, name='api_get_puntos_por_area'),
    path('seguimiento/', views.gestionar_seguimiento_diario, name='gestionar_seguimiento_diario'),
    path('mantenimiento/inoperativos/', views.vista_inoperativos, name='vista_inoperativos'),
    path('mantenimiento/marcar-operativo/<str:tipo_item>/<int:item_id>/', views.marcar_operativo, name='marcar_operativo'),
    path('reportes/tabla-portatiles/', views.vista_tabla_portatiles, name='vista_tabla_portatiles'),
    path('dispositivo/<int:dispositivo_id>/observaciones/', views.get_observaciones_json, name='get_observaciones_json'),
    path('dispositivo/<int:dispositivo_id>/observaciones/add/', views.add_observacion_json, name='add_observacion_json'),
    path('certificados/configurar-lote/', views.configurar_lote_certificacion, name='configurar_lote_certificacion'),
    path('certificados/limpiar-lote/', views.limpiar_lote_certificacion, name='limpiar_lote_certificacion'),
    path('programas/<int:programa_id>/certificados/', views.ver_certificados_programa, name='ver_certificados_programa'),
    path('certificados/lote/upload-anexo-temporal/', views.upload_anexo_temporal, name='upload_anexo_temporal'),

    path('certificados/anexos/agregar/', views.agregar_anexos_certificado, name='agregar_anexos_certificado'),

    path('exportar/', views.exportar_indice, name='exportar_indice'),
    path('exportar/dispositivos-portatiles/', views.exportar_portatiles_excel, name='exportar_portatiles_excel'),
    path('exportar/registros-flujo/', views.exportar_registros_diarios_excel, name='exportar_registros_excel'),
    path('exportar/dispositivos-fijos/complejo/', views.exportar_fijos_excel_certificado, name='exportar_fijos_excel_complejo'),
    path('exportar/dispositivos-fijos/', views.exportar_fijos_excel, name='exportar_fijos_excel'),
    path('exportar/progrmas/', views.exportar_programas_excel, name='exportar_programas_excel'),
    path('exportar/mantenimiento/', views.exportar_mantenimiento_indice, name='exportar_mantenimiento_indice'),
    path('exportar/mantenimiento/generar/', views.exportar_mantenimiento_excel, name='exportar_mantenimiento_excel'),
    path('exportar/fijos-por-area/<str:area_general>/', views.exportar_fijos_por_area, name='exportar_fijos_por_area'),
    path('dispositivos/<int:dispositivo_id>/cardex/', views.exportar_cardex_excel, name='exportar_cardex_excel'),
    path('exportar/reportes/', views.exportar_reportes_excel, name='exportar_reportes_excel'),
    path('exportar/seguimiento/', views.exportar_seguimiento_excel, name='exportar_seguimiento_excel'),
]