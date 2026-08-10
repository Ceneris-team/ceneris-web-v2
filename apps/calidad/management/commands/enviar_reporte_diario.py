# calidad/management/commands/enviar_reporte_diario.py (NUEVO ARCHIVO)

from django.core.management.base import BaseCommand
# ¡Importamos la función de trabajo pesado directamente!
from calidad.tasks import enviar_reporte_email_diario

class Command(BaseCommand):
    help = 'Ejecuta directamente la tarea de envío del reporte diario de EMOs.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando la ejecución de la tarea de envío de reporte...'))
        
        try:
            # Ejecutamos la función directamente, sin colas.
            enviar_reporte_email_diario()
            self.stdout.write(self.style.SUCCESS('La tarea finalizó su ejecución.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'La tarea falló con un error: {e}'))