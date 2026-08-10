# en personal/admin.py
from django.contrib import admin
from .models import Personal, AreaTrabajo

@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    # Campos que se mostrarán en la lista de personal
    list_display = ('nombre', 'apellido', 'cargo', 'area_trabajo', 'correo')
    
    # Campos que tendrán enlaces para ir a la vista de edición
    list_display_links = ('nombre', 'apellido')
    
    # Añade un campo de búsqueda
    search_fields = ('nombre', 'apellido', 'dni', 'correo')
    
    # Añade filtros en la barra lateral derecha
    list_filter = ('area_trabajo', 'cargo')
    
    # Organiza los campos en la vista de edición
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'apellido', 'dni')
        }),
        ('Contacto y Posición', {
            # Cambiamos 'areaTrabajo' por 'area_trabajo'
            'fields': ('cargo', 'area_trabajo', 'correo', 'telefono')
        }),
        ('Fotografía', {
            'fields': ('foto',)
        }),
    )

@admin.register(AreaTrabajo)
class AreaTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    
    # Agrega el enlace al campo 'nombre'
    list_display_links = ('nombre',)
    
    search_fields = ('nombre',)