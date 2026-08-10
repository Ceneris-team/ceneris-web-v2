from django.contrib import admin
from .models import (
    GerenciaGeneral, 
    Gerencia, 
    Superintendencia, 
    Puesto, 
    Agente, 
    Cargo, 
    Trabajador
)

# 1. Configuración para CARGOS
@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

# 2. Configuración para GERENCIAS
@admin.register(GerenciaGeneral)
class GerenciaGeneralAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Gerencia)
class GerenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'gerencia_general')
    list_filter = ('gerencia_general',)
    search_fields = ('nombre',)

# 3. Configuración para SUPERINTENDENCIAS
@admin.register(Superintendencia)
class SuperintendenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'gerencia')
    list_filter = ('gerencia',)
    search_fields = ('nombre',)

# 4. Configuración para PUESTOS (Opcional si lo harás por vista, pero útil aquí)
@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'superintendencia')
    search_fields = ('nombre',)
    list_filter = ('superintendencia',)

# 5. Configuración para AGENTES
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

# 6. Configuración para TRABAJADORES
@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'dni', 'cargo', 'telefono')
    search_fields = ('nombre', 'ap_paterno', 'dni')
    list_filter = ('cargo',)