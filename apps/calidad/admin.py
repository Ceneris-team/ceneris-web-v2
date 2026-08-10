from django.contrib import admin
from .models import Clinica, ArchivoClinica, EMO, Control, ArchivoAdjuntoEMO

# ============================================================================
# ADMINISTRACIÓN DE CLÍNICAS Y ARCHIVOS ADJUNTOS
# ============================================================================

class ArchivoClinicaInline(admin.TabularInline):
    """
    Permite agregar/editar PDFs directamente desde la página de Clinica
    """
    model = ArchivoClinica
    extra = 1
    fields = ('descripcion', 'archivo_pdf', 'activo', 'fecha_carga')
    readonly_fields = ('fecha_carga', 'fecha_actualizacion')


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email_contacto', 'persona_contacto', 'imagen_fachada', 'google_maps_url')
    list_filter = ('nombre',)
    search_fields = ('nombre', 'direccion', 'telefono', 'email_contacto')
    inlines = [ArchivoClinicaInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'direccion', 'imagen_fachada')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email_contacto', 'persona_contacto')
        }),
        ('Ubicación', {
            'fields': ('google_maps_url',)
        }),
    )


@admin.register(ArchivoClinica)
class ArchivoClinicaAdmin(admin.ModelAdmin):
    list_display = ('clinica', 'descripcion', 'activo', 'fecha_carga')
    list_filter = ('clinica', 'activo', 'fecha_carga')
    search_fields = ('clinica__nombre', 'descripcion')
    readonly_fields = ('fecha_carga', 'fecha_actualizacion')
    fieldsets = (
        ('Información del Archivo', {
            'fields': ('clinica', 'descripcion', 'archivo_pdf')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_carga', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# ADMINISTRACIÓN DE EMOs
# ============================================================================

@admin.register(EMO)
class EMOAdmin(admin.ModelAdmin):
    list_display = ('id', 'trabajador', 'tipo_emo', 'fecha_programada', 'hora_examen', 'lugar_examen', 'estado', 'aptitud')
    list_filter = ('estado', 'aptitud', 'tipo_emo', 'fecha_programada', 'lugar_examen')
    search_fields = ('trabajador__nombres', 'trabajador__apellido_paterno', 'trabajador__dni')
    readonly_fields = ('fecha_realizacion', 'fecha_validacion_subsana', 'fecha_confirmacion')
    fieldsets = (
        ('Trabajador e Información', {
            'fields': ('trabajador', 'empresa', 'cargo', 'proyecto', 'subproyecto')
        }),
        ('Programación del EMO', {
            'fields': ('tipo_emo', 'fecha_programada', 'hora_examen', 'lugar_examen')
        }),
        ('Estado y Resultados', {
            'fields': ('estado', 'aptitud', 'restriccion', 'comentario')
        }),
        ('Archivos', {
            'fields': ('archivo_pdf', 'archivo_subsana', 'archivo_confirmacion')
        }),
        ('Subsanación', {
            'fields': ('subsana_validado', 'fecha_validacion_subsana'),
            'classes': ('collapse',)
        }),
        ('Confirmación de Lectura', {
            'fields': ('confirmado_por_habilitador', 'fecha_confirmacion', 'confirmado_por'),
            'classes': ('collapse',)
        }),
        ('Vencimiento', {
            'fields': ('fecha_vencimiento',)
        }),
    )


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ('emo', 'fecha_programada', 'descripcion', 'realizado')
    list_filter = ('realizado', 'fecha_programada')
    search_fields = ('emo__trabajador__nombres', 'descripcion')
    fieldsets = (
        ('Información del Control', {
            'fields': ('emo', 'descripcion', 'fecha_programada')
        }),
        ('Ejecución', {
            'fields': ('realizado', 'fecha_realizacion', 'archivo_adjunto')
        }),
    )


@admin.register(ArchivoAdjuntoEMO)
class ArchivoAdjuntoEMOAdmin(admin.ModelAdmin):
    list_display = ('emo', 'descripcion', 'archivo')
    list_filter = ('emo__tipo_emo',)
    search_fields = ('emo__trabajador__nombres', 'descripcion')

