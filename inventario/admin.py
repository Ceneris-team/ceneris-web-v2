# en inventario/admin.py
from django.contrib import admin
from .models import Insumo, ItemInsumo, Accesorio, RegistroReparacion

class ItemInsumoInline(admin.TabularInline):
    """Permite editar Items directamente en la página del Insumo."""
    model = ItemInsumo
    extra = 1 # Muestra un campo extra para añadir un nuevo item
    fields = ('numero_serie', 'codigo_interno', 'marca', 'modelo', 'estado')

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad_medida', 'costo_unitario_actual', 'stock_calculado')
    # Añade un enlace al campo 'nombre' para ir a la vista de edición
    list_display_links = ('nombre',)
    search_fields = ('nombre', 'descripcion')
    inlines = [ItemInsumoInline]

@admin.register(ItemInsumo)
class ItemInsumoAdmin(admin.ModelAdmin):
    list_display = ('numero_serie', 'insumo_padre', 'estado', 'fecha_prox_calibracion')
    # Añade un enlace al campo 'numero_serie' para ir a la vista de edición
    list_display_links = ('numero_serie',)
    search_fields = ('numero_serie', 'codigo_interno', 'insumo_padre__nombre')
    list_filter = ('estado', 'insumo_padre', 'marca')

@admin.register(Accesorio)
class AccesorioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'numero_serie', 'item_insumo')
    # Añade un enlace al campo 'nombre' para ir a la vista de edición
    list_display_links = ('nombre',)
    search_fields = ('nombre', 'numero_serie', 'item_insumo__numero_serie')

@admin.register(RegistroReparacion)
class RegistroReparacionAdmin(admin.ModelAdmin):
    list_display = ('item_insumo', 'fecha_reporte', 'costo')
    # Añade un enlace al campo 'item_insumo' para ir a la vista de edición
    list_display_links = ('item_insumo',)
    search_fields = ('item_insumo__numero_serie',)
    list_filter = ('fecha_reporte',)