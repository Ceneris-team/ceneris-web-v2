# calidad/management/commands/queue_daily_report.py (NUEVO ARCHIVO)

from django.core.management.base import BaseCommand
from django_q.tasks import async_task

class Command(BaseCommand):
    help = 'Pone en cola la tarea de envío del reporte diario de EMOs.'

    def handle(self, *args, **options):
        self.stdout.write('Poniendo en cola la tarea de envío de reporte...')
        
        # Esto no ejecuta la función, solo deja una "nota" en el buzón (Redis)
        # para que el Background Worker la recoja.
        async_task('calidad.tasks.enviar_reporte_email_diario')
        
        self.stdout.write(self.style.SUCCESS('¡Tarea puesta en cola exitosamente!'))