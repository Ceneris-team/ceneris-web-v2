# dashboard/admin.py
from django.contrib import admin, messages
from admin_panel.settings import db
from django.shortcuts import render
from .models import Sede, Area, Empresa, Cargo, CentroCosto, ConfiguracionTolerancia, ToleranciaAuditoria, Trabajador

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