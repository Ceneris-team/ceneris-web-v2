# en proyectos/admin.py
from django.contrib import admin
from .models import Proyecto, TareaP, SubTarea, RegistroActividad

class SubTareaInline(admin.TabularInline):
    model = SubTarea
    extra = 1
    fields = ('titulo', 'fecha_inicio', 'fecha_fin', 'completada')

class TareaPInline(admin.TabularInline):
    model = TareaP
    extra = 1
    fields = ('titulo', 'completada')

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio_calculada', 'fecha_fin_calculada', 'completada')
    # Añade un enlace al campo 'nombre' para ir a la vista de edición
    list_display_links = ('nombre',)
    search_fields = ('nombre', 'descripcion')
    list_filter = ('completada',)
    inlines = [TareaPInline]

@admin.register(TareaP)
class TareaPAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'completada')
    # Añade un enlace al campo 'titulo' para ir a la vista de edición
    list_display_links = ('titulo',)
    search_fields = ('titulo', 'proyecto__nombre')
    list_filter = ('proyecto', 'completada')
    inlines = [SubTareaInline]

@admin.register(SubTarea)
class SubTareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tarea', 'fecha_inicio', 'fecha_fin', 'completada')
    # Añade un enlace al campo 'titulo' para ir a la vista de edición
    list_display_links = ('titulo',)
    search_fields = ('titulo', 'tarea__titulo')
    list_filter = ('tarea__proyecto', 'completada')
    # Para campos ManyToMany, filter_horizontal es mucho más amigable
    filter_horizontal = ('personal_asignado',)

@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    """
    Configuración del Admin para el historial de actividad.
    Está diseñado para ser de solo lectura.
    """
    list_display = ('timestamp', 'usuario', 'accion', 'get_content_object_display')
    list_filter = ('accion', 'timestamp', 'content_type')
    search_fields = ('usuario__username', 'descripcion')

    # Hacemos que la interfaz sea de solo lectura para evitar modificaciones accidentales
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Objeto Modificado')
    def get_content_object_display(self, obj):
        return f"{obj.content_type.model.title()}: {str(obj.content_object)}"