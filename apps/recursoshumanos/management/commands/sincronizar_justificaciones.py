# recursoshumanos/management/commands/sincronizar_justificaciones.py
from django.core.management.base import BaseCommand
from recursoshumanos.servicios_justificaciones import sincronizar_justificaciones_erp

class Command(BaseCommand):
    help = 'Sincroniza las ausencias justificadas (descansos médicos, vacaciones) desde el ERP'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando sincronización de justificaciones desde el ERP...'))
        
        try:
            nuevos = sincronizar_justificaciones_erp()
            self.stdout.write(self.style.SUCCESS(f'¡Éxito! Se generaron {nuevos} días justificados.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error de sincronización: {str(e)}'))