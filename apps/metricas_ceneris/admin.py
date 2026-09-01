from django.contrib import admin

from .models import EvaluacionMensual, Puntaje, NotaConocimiento


@admin.register(NotaConocimiento)
class NotaConocimientoAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'fecha', 'nota', 'comentario', 'fecha_creacion')
    list_filter = ('fecha',)
    search_fields = ('trabajador__dni', 'trabajador__nombres', 'trabajador__apellido_paterno')
    autocomplete_fields = ('trabajador',)
    ordering = ('-fecha',)


class PuntajeInline(admin.TabularInline):
    model = Puntaje
    extra = 0


@admin.register(EvaluacionMensual)
class EvaluacionMensualAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'tipo', 'fecha_evaluacion', 'promedio_final', 'evaluador')
    list_filter = ('tipo', 'fecha_evaluacion')
    search_fields = ('trabajador__dni', 'trabajador__nombres', 'trabajador__apellido_paterno')
    inlines = [PuntajeInline]
    ordering = ('-fecha_evaluacion',)
