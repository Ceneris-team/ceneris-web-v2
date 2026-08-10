from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.models import User
from datetime import timedelta

from calidad.models import EMO


class Command(BaseCommand):
    help = 'Envía reporte semanal de EMOs programados a todos los usuarios con rol Doctor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra el resumen por consola sin enviar emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoy = timezone.now().date()
        limite_por_vencer = hoy + timedelta(days=7)

        # --- 1. Obtener doctores ---
        doctores = User.objects.filter(
            groups__name='Doctor',
            is_active=True,
            email__isnull=False,
        ).exclude(email='')

        if not doctores.exists():
            self.stdout.write(self.style.WARNING('No hay usuarios con el rol "Doctor" o ninguno tiene email. Abortando.'))
            return

        # --- 2. Calcular métricas globales de EMOs Programados ---
        emos_programados = EMO.objects.filter(
            estado='Programado'
        ).select_related(
            'trabajador', 'empresa', 'proyecto', 'lugar_examen', 'cargo'
        ).order_by('fecha_programada')

        total = emos_programados.count()

        emos_vencidos = []
        emos_por_vencer = []
        emos_futuros = []

        for emo in emos_programados:
            if not emo.fecha_programada:
                emos_futuros.append(emo)
                continue
            dias = (emo.fecha_programada - hoy).days
            emo.dias_diferencia = dias
            if dias < 0:
                emos_vencidos.append(emo)
            elif dias <= 7:
                emos_por_vencer.append(emo)
            else:
                emos_futuros.append(emo)

        context = {
            'hoy': hoy,
            'total': total,
            'emos_vencidos': emos_vencidos,
            'emos_por_vencer': emos_por_vencer,
            'emos_futuros': emos_futuros,
            'total_vencidos': len(emos_vencidos),
            'total_por_vencer': len(emos_por_vencer),
            'total_futuros': len(emos_futuros),
        }

        if dry_run:
            self.stdout.write(f'\n{"="*55}')
            self.stdout.write(f'  DRY RUN — Reporte Semanal Doctor')
            self.stdout.write(f'{"="*55}')
            self.stdout.write(f'  Total EMOs programados : {total}')
            self.stdout.write(f'  Vencidos               : {len(emos_vencidos)}')
            self.stdout.write(f'  Proximos a realizarse  : {len(emos_por_vencer)}')
            self.stdout.write(f'  Con fecha futura       : {len(emos_futuros)}')
            self.stdout.write(f'\n  Destinatarios ({doctores.count()}):')
            for d in doctores:
                self.stdout.write(f'    - {d.username} <{d.email}>')
            self.stdout.write(f'{"="*55}\n')
            return

        # --- 3. Enviar email a cada doctor ---
        asunto = f"Resumen Semanal de EMOs Programados — {hoy.strftime('%d/%m/%Y')}"
        enviados = 0
        errores = 0

        for doctor in doctores:
            context['doctor'] = doctor
            try:
                html_content = render_to_string(
                    'calidad/emails/reporte_semanal_doctor.html', context
                )
                msg = EmailMultiAlternatives(
                    subject=asunto,
                    body=f"Reporte semanal: {total} EMOs programados ({len(emos_vencidos)} vencidos, {len(emos_por_vencer)} proximos).",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[doctor.email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                enviados += 1
                self.stdout.write(f'  Email enviado a {doctor.email}')
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f'  Error enviando a {doctor.email}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nReporte semanal doctor completado: {enviados} enviados, {errores} errores.'
        ))
