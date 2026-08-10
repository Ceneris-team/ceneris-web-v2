from django.core.management.base import BaseCommand, CommandError

from calidad.models import EMO
from calidad.services import notificar_doctores


class Command(BaseCommand):
    help = (
        'Envía un correo de prueba (el mismo que recibe salud.ocupacional) a un '
        'correo arbitrario, usando los EMOs programados reales en este momento. '
        'No envía nada a los destinatarios reales.'
    )

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Correo de destino para la prueba')
        parser.add_argument(
            '--emo-id',
            type=int,
            default=None,
            help=(
                'ID de un EMO ya existente para simular la versión de "nuevo EMO '
                'programado" (con la tarjeta destacada), en vez de la versión de '
                'resumen general.'
            ),
        )

    def handle(self, *args, **options):
        email = options['email']
        emo_id = options['emo_id']

        nuevo_emo = None
        if emo_id is not None:
            try:
                nuevo_emo = EMO.objects.get(id=emo_id)
            except EMO.DoesNotExist:
                raise CommandError(f'No existe un EMO con id={emo_id}')

        try:
            notificar_doctores(nuevo_emo=nuevo_emo, destinatarios_override=[email])
        except Exception as e:
            raise CommandError(f'Error al enviar el correo de prueba: {e}')

        self.stdout.write(self.style.SUCCESS(f'Correo de prueba enviado a {email}'))
