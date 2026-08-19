from django.contrib import admin

from .models import EmailLog, PlantillaEmail


@admin.register(PlantillaEmail)
class PlantillaEmailAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'asunto', 'activa', 'updated_at')
    list_filter = ('activa',)
    search_fields = ('nombre', 'asunto')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        'asunto_corto', 'destinatario', 'estado', 'intentos',
        'created_at', 'enviado_at',
    )
    list_filter = ('estado', 'created_at')
    search_fields = ('destinatario', 'asunto')
    readonly_fields = (
        'destinatario', 'cc', 'bcc', 'asunto', 'cuerpo_html', 'cuerpo_texto',
        'remitente', 'plantilla', 'contexto_json', 'estado', 'intentos',
        'max_intentos', 'proximo_reintento', 'ultimo_error',
        'sendgrid_message_id', 'created_at', 'enviado_at', 'updated_at',
    )
    date_hierarchy = 'created_at'

    def asunto_corto(self, obj):
        return obj.asunto[:60] + '...' if len(obj.asunto) > 60 else obj.asunto
    asunto_corto.short_description = 'Asunto'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
