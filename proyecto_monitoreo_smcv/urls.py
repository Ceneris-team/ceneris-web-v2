# proyecto_monitoreo_smcv/urls.py
from django.urls import path
from . import views

from .views import (
    DashboardYeniView, 
    SoporteTecnicoView, 
    ProgramacionView, 
    EvaluacionView, 
    CapacitacionView, 
    SupervisorView,
    #TrabajadorListView,
    #TrabajadorCreateView,
    DiagnosticoCreateView, 
    MantenimientoCreateView,
    CalibracionCreateView,
    OperatividadCreateView,
    InventarioGeneralView,
    MatrizMantenimientoView,
    generar_pdf_diagnostico, 
    generar_pdf_mantenimiento,
    generar_pdf_operatividad,
    generar_pdf_calibracion,
    generar_excel_calibracion,
    exportar_inventario_pdf,
    HistorialDiagnosticosView,
    HistorialMantenimientosView,
    HistorialCalibracionesView,
    HistorialOperatividadView,
    HistorialCambioAccesorioCreateView,
    VibrometrosView,
    InventarioRepuestosView,
    HistorialCambiosView,
    DosimetrosView,
    CambioDosimetroCreateView,
    HistorialCambiosDosimetrosView,
    CambioBombaCreateView,
    BombasView,
    HistorialCambiosBombasView,
    actualizar_dispositivo_api,
    actualizar_cambio_api,
    actualizar_accesorio_api,
    actualizar_stock_api,
    InspeccionEspecificaCreateView,
    generar_pdf_inspeccion_especifica,
    HistorialInspeccionesView,
    InspeccionConjuntaCreateView,
    generar_pdf_inspeccion_conjunta,
    HistorialConjuntasView,
    ProgramaCreateView,
    FilaCronogramaCreateView, 
    generar_pdf_programa,
    DetalleProgramaView,
    ListaProgramasView,
    toggle_ejecucion_api,
)

from proyecto_monitoreo_smcv import views as proyecto_monitoreo_smcv_views
from .views import lista_ubicaciones, crear_ubicacion, editar_ubicacion, eliminar_ubicacion

app_name = 'proyecto_monitoreo_smcv'

urlpatterns = [
    # Vistas Basadas en Clases
    path('dashboard/', views.DashboardYeniView.as_view(), name='dashboard'),
    path('soporte/', views.SoporteTecnicoView.as_view(), name='soporte'),
    path('programacion/', views.ProgramacionView.as_view(), name='programacion'),
    path('evaluacion/', views.EvaluacionView.as_view(), name='evaluacion'),
    path('capacitacion/', views.CapacitacionView.as_view(), name='capacitacion'),
    path('supervisor/', views.SupervisorView.as_view(), name='supervisor'),

    # Trabajador
    path('catalogos/trabajadores/', views.lista_trabajador, name='lista_trabajador'),
    path('catalogos/trabajadores/nuevo/', views.crear_trabajador, name='crear_trabajador'),

    # Agente
    path('catalogos/agentes/', views.lista_agente, name='lista_agentes'),
    path('catalogos/agentes/nuevo/', views.crear_agente, name='crear_agente'),

    # Puesto
    path('catalogos/puestos/', views.lista_puesto, name='lista_puestos'),
    path('catalogos/puestos/nuevo/', views.crear_puesto, name='crear_puesto'),

    # Gerencia General
    path('catalogos/gerencias-generales/', views.gerencia_general_lista, name='lista_gerencias_generales'),
    path('catalogos/gerencias-generales/nuevo/', views.crear_gerencia_general, name='crear_gerencia_general'),

    # Gerencia
    path('catalogos/gerencias/', views.gerencia_lista, name='lista_gerencias'),
    path('catalogos/gerencias/nuevo/', views.crear_gerencia, name='crear_gerencia'),

    # Superintendencia
    path('catalogos/superintendencias/', views.superintendencia_lista, name='lista_superintendencias'),
    path('catalogos/superintendencias/nuevo/', views.crear_superintendencia, name='crear_superintendencia'),

    # Ubicaciones
    path('catalogos/ubicaciones/', lista_ubicaciones, name='lista_ubicaciones'),
    path('catalogos/ubicaciones/nuevo/', crear_ubicacion, name='crear_ubicacion'),
    path('catalogos/ubicaciones/<int:pk>/editar/', editar_ubicacion, name='editar_ubicacion'),
    path('catalogos/ubicaciones/<int:pk>/eliminar/', eliminar_ubicacion, name='eliminar_ubicacion'),

    # Importar
    path('planificacion/importar/', views.importar_plan_mensual, name='importar_plan'),
    path('catalogos/gerencias/', views.gerencia_lista, name='lista_gerencias'),
    path('catalogos/gerencias/nuevo/', views.crear_gerencia, name='crear_gerencia'),

    # Programacion mensual
    path('planificacion/mensual/', views.plan_mensual_index, name='plan_mensual_index'),
    path('planificacion/mensual/confirmar/', views.confirmar_importacion, name='confirmar_importacion'),
    path('planificacion/mensual/eliminar/<int:anio>/<int:mes>/', views.eliminar_plan_mensual, name='eliminar_plan'),
    path('planificacion/mensual/<int:anio>/<int:mes>/semanas/', views.tablero_mensual_semanas, name='tablero_mensual'),
    path('planificacion/mensual/<int:anio>/<int:mes>/semana/<int:nro_semana>/', views.asignar_carga_semanal, name='asignar_carga_semanal'),

    # Programacion semanal
    path('planificacion/semanal/control/', views.control_semanal_dashboard, name='control_semanal_base'),
    path('planificacion/semanal/control/<int:anio>/<int:mes>/<int:semana>/', views.control_semanal_dashboard, name='control_semanal'),
    path('planificacion/mensual/<int:anio>/<int:mes>/semana/<int:nro_semana>/dias/', views.gestion_dias_semana, name='gestion_dias_semana'),
    path('planificacion/diaria/crear/<str:fecha_str>/', views.crear_programacion_diaria, name='crear_prog_diaria'),
    path('planificacion/diaria/', views.programacion_diaria_index, name='programacion_diaria_index'),
    #path('planificacion/diaria/', programacion_diaria_index, name='programacion_diaria_index'),
    path('planificacion/diaria/<int:anio>/<int:mes>/semana/<int:nro_semana>/', views.vista_semana_operativa, name='vista_semana_operativa'),
    
    # ==========================================
    # SOPORTE TÉCNICO
    # ========================================== 
    path('soporte/', SoporteTecnicoView.as_view(), name='soporte_index'),

    # APIs
    path('api/actualizar-dispositivo/', actualizar_dispositivo_api, name='api_update_device'),
    path('api/actualizar-accesorio/', actualizar_accesorio_api, name='api_update_accesorio'),
    path('api/actualizar-cambio/', actualizar_cambio_api, name='api_update_cambio'),
    path('api/actualizar-stock/', actualizar_stock_api, name='api_update_stock'),
    path('api/toggle-ejecucion/', toggle_ejecucion_api, name='api_toggle_ejecucion'),
    
    # Formularios
    path('soporte/diagnostico/nuevo/', DiagnosticoCreateView.as_view(), name='crear_diagnostico'),
    path('soporte/mantenimiento/nuevo/', MantenimientoCreateView.as_view(), name='crear_mantenimiento'),
    path('soporte/operatividad/nuevo/', OperatividadCreateView.as_view(), name='crear_operatividad'),
    path('soporte/calibracion/nuevo/', CalibracionCreateView.as_view(), name='crear_calibracion'),
    path('inventario/vibrometros/cambio/', HistorialCambioAccesorioCreateView.as_view(), name='crear_cambio_componente'),
    path('inventario/dosimetros/cambio/', CambioDosimetroCreateView.as_view(), name='crear_cambio_dosimetro'),
    path('inventario/bombas/cambio/', CambioBombaCreateView.as_view(), name='crear_cambio_bomba'),
    path('inspeccion/especifica/nueva/', InspeccionEspecificaCreateView.as_view(), name='crear_inspeccion_especifica'),
    path('inspeccion/conjunta/nueva/', InspeccionConjuntaCreateView.as_view(), name='crear_inspeccion_conjunta'),
    path('programas/nuevo/', ProgramaCreateView.as_view(), name='crear_programa'),
    path('programa/<int:programa_id>/agregar-fila/', FilaCronogramaCreateView.as_view(), name='agregar_fila_programa'),
    
    # Exportar PDF
    path('soporte/diagnostico/<int:pk>/pdf/', generar_pdf_diagnostico, name='pdf_diagnostico'),
    path('soporte/mantenimiento/<int:pk>/pdf/', generar_pdf_mantenimiento, name='pdf_mantenimiento'),
    path('soporte/operatividad/<int:pk>/pdf/', generar_pdf_operatividad, name='pdf_operatividad'),
    path('soporte/calibracion/<int:pk>/pdf/', generar_pdf_calibracion, name='pdf_calibracion'),
    path('inventario/general/pdf/', exportar_inventario_pdf, name='exportar_inventario_pdf'),
    path('inspeccion/especifica/<int:pk>/pdf/', generar_pdf_inspeccion_especifica, name='pdf_inspeccion_especifica'),
    path('inspeccion/conjunta/<int:pk>/pdf/', generar_pdf_inspeccion_conjunta, name='pdf_inspeccion_conjunta'),
    path('programas/<int:pk>/pdf/', generar_pdf_programa, name='pdf_programa'),

    # Exportar EXCEL
    path('soporte/calibracion/<int:pk>/excel/', generar_excel_calibracion, name='excel_calibracion'),

    # Ver TABLAS
    path('soporte/tablas/general/', InventarioGeneralView.as_view(), name='inventario_general'),
    path('soporte/tablas/matriz/', MatrizMantenimientoView.as_view(), name='matriz_mantenimiento'),
    path('soporte/cambios/vibrometros/', VibrometrosView.as_view(), name='vibrometros_view'),
    path('soporte/inventario/repuestos/', InventarioRepuestosView.as_view(), name='inventario_repuestos'),
    path('inventario/dosimetros/', DosimetrosView.as_view(), name='dosimetros_view'),
    path('inventario/bombas/', BombasView.as_view(), name='bombas_view'),
    path('historial/inspecciones-especificas/', HistorialInspeccionesView.as_view(), name='historial_inspecciones'),
    path('historial/inspecciones-conjuntas/', HistorialConjuntasView.as_view(), name='historial_conjuntas'),
    path('programa/', ListaProgramasView.as_view(), name='lista_programas'),
    path('programa/<int:pk>/', DetalleProgramaView.as_view(), name='detalle_programa'),


    # HISTORIALES COMPLETOS
    path('historial/diagnosticos/', HistorialDiagnosticosView.as_view(), name='historial_diagnosticos'),
    path('historial/mantenimientos/', HistorialMantenimientosView.as_view(), name='historial_mantenimientos'),
    path('historial/calibraciones/', HistorialCalibracionesView.as_view(), name='historial_calibraciones'),
    path('historial/operatividad/', HistorialOperatividadView.as_view(), name='historial_operatividad'),
    path('historial/cambios-componentes/', HistorialCambiosView.as_view(), name='historial_cambios_componentes'),
    path('historial/cambios-dosimetros/', HistorialCambiosDosimetrosView.as_view(), name='historial_cambios_dosimetros'),
    path('historial/cambios-bombas/', HistorialCambiosBombasView.as_view(), name='historial_cambios_bombas'),
]


