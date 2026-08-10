from django.contrib import admin
from .models import Empresa, Contacto, ProcesoCotizacion, Cotizaciones, LogAcciones

# Para mejorar la visualización en el admin
class ProcesoCotizacionAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'fecha_citacion', 'usuario_agenda', 'fecha_encuentro', 'usuario_encuentro', 'cotizacion_final')
    list_filter = ('usuario_agenda', 'usuario_encuentro')
    search_fields = ('empresa__nombre', 'contacto__nombre')

class CotizacionesAdmin(admin.ModelAdmin):
    list_display = ('get_empresa', 'fecha_creacion', 'usuario_creador', 'estado')
    list_filter = ('estado', 'usuario_creador')
    search_fields = ('procesocotizacion__empresa__nombre',)

    # Función para obtener el nombre de la empresa a través de la relación
    def get_empresa(self, obj):
        if obj.procesocotizacion:
            return obj.procesocotizacion.empresa.nombre
        return "N/A"
    get_empresa.short_description = 'Empresa'
    get_empresa.admin_order_field = 'procesocotizacion__empresa'


# Registro de los modelos
admin.site.register(Empresa)
admin.site.register(Contacto)
admin.site.register(ProcesoCotizacion, ProcesoCotizacionAdmin)
admin.site.register(Cotizaciones, CotizacionesAdmin)
admin.site.register(LogAcciones)