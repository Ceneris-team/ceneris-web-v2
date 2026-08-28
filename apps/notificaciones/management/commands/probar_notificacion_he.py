from django.core.management.base import BaseCommand

from notificaciones.services import SendGridEmailService


class Command(BaseCommand):
    help = 'Envía un correo de prueba simulando una notificación de solicitud de horas extra'

    def add_arguments(self, parser):
        parser.add_argument('email', help='Email destino para la prueba')

    def handle(self, *args, **options):
        email = options['email']
        self.stdout.write(f'Enviando correo de prueba a {email}...')

        from datetime import date

        contexto = {
            'trabajador_nombre': 'Juan Carlos Pérez López',
            'trabajador_dni': '12345678',
            'trabajador_area': 'Operaciones',
            'fecha_horas_extra': '19/08/2026',
            'cantidad_horas': '2.5',
            'justificacion': 'Se requirió completar el mantenimiento preventivo del equipo de soldadura antes del cierre del turno.',
            'origen': 'Aplicación móvil',
            'enlace_aprobacion': 'http://localhost:8000/recursoshumanos/horas-extra/panel-aprobacion/',
            'anio': date.today().year,
        }

        servicio = SendGridEmailService()
        log = servicio.enviar_con_django_template(
            destinatario=email,
            asunto='[PRUEBA] Nueva solicitud de horas extra — Juan Carlos Pérez López',
            template_name='notificaciones/emails/solicitud_horas_extra.html',
            contexto=contexto,
        )

        if log.estado == 'ENVIADO':
            self.stdout.write(self.style.SUCCESS(f'Correo enviado OK (ID: {log.sendgrid_message_id})'))
        else:
            self.stdout.write(self.style.ERROR(f'Error: {log.ultimo_error}'))
