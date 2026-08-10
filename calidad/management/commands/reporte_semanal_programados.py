from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from calidad.models import EMO
from calidad.services import notificar_doctores

class Command(BaseCommand):
    help = 'Envía un reporte semanal de los EMOs programados para los próximos días'

    def handle(self, *args, **kwargs):
        self.stdout.write("Generando reporte de EMOs Programados...")

        # --- CONFIGURACIÓN ---
        # Correo al que llegará el reporte semanal
        destinatarios = ['salud.ocupacional@ceneris.com'] 
        
        hoy = timezone.now().date()
        # Rango: Desde hoy hasta dentro de 7 días (Semanal)
        fecha_limite = hoy + timedelta(days=7)

        # --- CONSULTA ---
        # Filtramos solo los que están en estado 'Programado' y fecha futura cercana
        emos_programados = EMO.objects.filter(
            estado='Programado',
            fecha_programada__range=(hoy, fecha_limite),
            trabajador__activo=True
        ).filter(
            Q(trabajador__fecha_cese__isnull=True) | Q(trabajador__fecha_cese__gt=hoy)
        ).select_related(
            'trabajador', 'empresa', 'proyecto', 'subproyecto', 'lugar_examen'
        ).order_by('fecha_programada')

        # Si quieres que traiga TODOS los programados futuros sin límite de fecha, 
        # cambia la consulta anterior por:
        # emos_programados = EMO.objects.filter(estado='Programado', fecha_programada__gte=hoy).order_by('fecha_programada')

        if emos_programados.exists():
            # Calcular días faltantes para visualización
            for emo in emos_programados:
                if emo.fecha_programada:
                    emo.dias_faltan = (emo.fecha_programada - hoy).days
                else:
                    emo.dias_faltan = 0

            # --- PREPARAR CORREO ---
            context = {
                'emos': emos_programados,
                'hoy': hoy,
                'rango_fin': fecha_limite
            }

            try:
                html_content = render_to_string('calidad/emails/reporte_semanal_programados.html', context)
                asunto = f"📅 Agenda Semanal de EMOs - Semana del {hoy.strftime('%d/%m')}"

                msg = EmailMultiAlternatives(
                    subject=asunto,
                    body="Se adjunta la lista de EMOs programados para esta semana.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=destinatarios
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                self.stdout.write(self.style.SUCCESS(f'Reporte enviado a {len(destinatarios)} destinatarios con {emos_programados.count()} registros.'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error al enviar el correo: {e}'))
        else:
            self.stdout.write(self.style.WARNING('No hay EMOs programados para la próxima semana. No se envió correo.'))

        # --- NOTIFICAR PANORAMA DE EMOS PROGRAMADOS ---
        # Además del reporte de la semana a salud.ocupacional@ceneris.com (arriba),
        # se envía el panorama completo de EMOs 'Programado' (total, vencidos y
        # programados hasta la fecha) a DESTINATARIOS_EMO_PROGRAMADOS, con copia.
        try:
            notificar_doctores()
            self.stdout.write(self.style.SUCCESS('Notificación de EMOs programados enviada.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al notificar EMOs programados: {e}'))