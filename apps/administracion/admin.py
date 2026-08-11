from django.contrib import admin
from .models import Agente, Feriado


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
	list_display = ('nombre_agente', 'precio_unitario', 'activo')
	search_fields = ('nombre_agente',)
	list_filter = ('activo',)


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'fecha', 'tipo', 'ambito')
	list_filter = ('tipo', 'ambito')
	search_fields = ('nombre',)
	ordering = ('-fecha',)
	date_hierarchy = 'fecha'
