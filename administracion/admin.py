from django.contrib import admin
from .models import Agente


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
	list_display = ('nombre_agente', 'precio_unitario', 'activo')
	search_fields = ('nombre_agente',)
	list_filter = ('activo',)
