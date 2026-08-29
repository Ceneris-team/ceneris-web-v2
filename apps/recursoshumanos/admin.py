# dashboard/admin.py
from django.contrib import admin, messages
from admin_panel.settings import db
from django.shortcuts import render
from .models import Sede, Area, Empresa, Cargo, CentroCosto, ConfiguracionTolerancia, ToleranciaAuditoria, Trabajador, EventoLoginOffline, MarcaSinHorarioAuditoria, Sancion, Asistencia

# Creamos una acción personalizada para desvincular dispositivos
@admin.action(description="Desvincular dispositivo seleccionado")
def desvincular_dispositivo(modeladmin, request, queryset):
    for dni in queryset.values_list('pk', flat=True):
        try:
            doc_ref = db.collection('trabajadores').document(dni)
            doc_ref.update({'deviceIdVinculado': None})
        except Exception as e:
            modeladmin.message_user(request, f"Error al desvincular DNI {dni}: {e}", messages.ERROR)
    modeladmin.message_user(request, "Dispositivos desvinculados con éxito.", messages.SUCCESS)

# Definimos la interfaz del admin
class TrabajadorAdmin(admin.ModelAdmin):
    # Esta clase no usa un modelo de DB, así que sobreescribimos los métodos
    
    def get_queryset(self, request):
        # Este método es un placeholder, ya que no usamos la DB de Django
        return super().get_queryset(request).none()

    def changelist_view(self, request, extra_context=None):
        # La vista principal que lista todos los trabajadores desde Firestore
        trabajadores_ref = db.collection('trabajadores').stream()
        trabajadores_list = [doc.to_dict() for doc in trabajadores_ref]
        
        context = {
            'title': 'Gestión de Trabajadores',
            'trabajadores': trabajadores_list,
        }
        return render(request, 'admin/trabajadores_list.html', context)
    
    # Necesitamos registrar el modelo para que aparezca en el menú
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Trabajador)
class TrabajadorAdminInterface(admin.ModelAdmin):
    list_display = ('dni', 'nombre_completo', 'cargo', 'area', 'user', 'activo')
    list_filter = ('activo', 'area', 'sede')
    search_fields = ('dni', 'nombres', 'apellido_paterno', 'apellido_materno', 'user__username')
    raw_id_fields = ('user',)
    autocomplete_fields = ['area', 'sede']

# Registrar modelos básicos para gestión
@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'direccion']
    ordering = ['nombre']

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc', 'telefono']
    search_fields = ['nombre', 'ruc']

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['codigo', 'nombre']

@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['codigo', 'nombre']

@admin.register(ConfiguracionTolerancia)
class ConfiguracionToleranciaAdmin(admin.ModelAdmin):
    list_display = ['sede', 'tipo_horario', 'minutos_tolerancia', 'activo', 'actualizado_en']
    list_filter = ['sede', 'tipo_horario', 'activo']
    search_fields = ['sede__nombre']

@admin.register(ToleranciaAuditoria)
class ToleranciaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['sede_nombre', 'tipo_horario', 'minutos_anteriores', 'minutos_nuevos', 'usuario', 'creado_en']
    list_filter = ['tipo_horario']
    search_fields = ['sede_nombre']
    ordering = ['-creado_en']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MarcaSinHorarioAuditoria)
class MarcaSinHorarioAuditoriaAdmin(admin.ModelAdmin):
    """Quien habilito a quien a marcar sin horario (solo lectura)."""
    list_display = ['trabajador_nombre', 'trabajador_dni', 'habilitado_nuevo', 'hasta_nuevo', 'usuario', 'creado_en']
    list_filter = ['habilitado_nuevo']
    search_fields = ['trabajador_nombre', 'trabajador_dni']
    ordering = ['-creado_en']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EventoLoginOffline)
class EventoLoginOfflineAdmin(admin.ModelAdmin):
    """CAV-83: auditoria de logins realizados sin conexion (solo lectura)."""
    list_display = ['trabajador', 'device_id', 'fecha_hora_offline', 'fecha_hora_reportado']
    list_filter = ['fecha_hora_offline']
    search_fields = ['trabajador__dni', 'trabajador__nombres', 'trabajador__apellido_paterno', 'device_id']
    ordering = ['-fecha_hora_offline']
    readonly_fields = ['trabajador', 'device_id', 'fecha_hora_offline', 'fecha_hora_reportado']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Sancion)
class SancionAdmin(admin.ModelAdmin):
    list_display = ['trabajador', 'tipo', 'fecha_sancion', 'creado_por', 'fecha_creacion']
    list_filter = ['tipo', 'fecha_sancion']
    search_fields = ['trabajador__dni', 'trabajador__nombres', 'trabajador__apellido_paterno', 'contexto']
    ordering = ['-fecha_sancion', '-fecha_creacion']


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    """Revision de marcaciones, con foco en las observadas por geocerca.

    Es la superficie minima para que RRHH pueda decidir sobre una marca fuera
    de zona: la validacion la hace el servidor (`servicios_geocerca.py`) pero
    NO la rechaza, asi que alguien tiene que poder verlas y filtrarlas.
    Solo lectura: una marcacion es un hecho registrado; corregirla a mano aca
    dejaria el tareo recalculado fuera de sincronia.
    """
    list_display = [
        'timestamp', 'usuario', 'tipo_marcacion', 'origen',
        'estado_geocerca', 'ubicacion_validada', 'distancia_geocerca_m',
        'nombre_ubicacion',
    ]
    list_filter = ['estado_geocerca', 'origen', 'tipo_marcacion', 'timestamp']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name', 'device_id']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_select_related = ['usuario', 'ubicacion_validada']

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
