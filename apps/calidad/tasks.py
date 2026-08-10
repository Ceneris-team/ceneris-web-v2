from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from calidad.models import EMO, Control

class Command(BaseCommand):
    help = 'Envía alertas de vencimientos segmentadas por proyecto y destinatarios'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando proceso de alertas masivas...")
        
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=30) # Anticipación de un mes

        # ==============================================================================
        # GRUPO 1: REPORTE GLOBAL (Todos los proyectos)
        # ==============================================================================
        self.enviar_bloque(
            titulo="Reporte Global de Vencimientos (Todo Ceneris)",
            #destinatarios=['asistente02.rrhh@ceneris.com', 'planner@ceneris.com'],
            destinatarios=['saavedragarciafabio@gmail.com'],
            filtro_proyectos=None, # None = Todos los proyectos
            incluir_emos=True,
            incluir_controles=True,
            hoy=hoy,
            fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 2: CERRO VERDE (Solo proyectos específicos)
        # ==============================================================================
        # ¡IMPORTANTE!: Reemplaza 'PRO-CV' con los códigos reales de Cerro Verde
        codigos_cerro_verde = ['PRO-CV', 'PRO-SMCV', 'CVERDE'] 
        
        self.enviar_bloque(
            titulo="Reporte Vencimientos - Proyecto Cerro Verde",
            destinatarios=['fabio_saavedra@usmp.pe'],
            #destinatarios=['asistente03.rrhh@ceneris.com', 'consultor01@ceneris.com', 'consultor02@ceneris.com'],
            filtro_proyectos=codigos_cerro_verde,
            incluir_emos=True,
            incluir_controles=True,
            hoy=hoy,
            fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 3: ANTAPACCAY (Solo proyectos específicos)
        # ==============================================================================
        codigos_antapaccay = ['PRO-ANT-HIDRO', 'PRO-CMA']
        
        self.enviar_bloque(
            titulo="Reporte Vencimientos - Proyecto Antapaccay/CMA",
            destinatarios=['saavedragarciafabio@gmail.com'],
            #destinatarios=['ingenierohse.cma@ceneris.com', 'ssoma@ceneris.com'],
            filtro_proyectos=codigos_antapaccay,
            incluir_emos=True,
            incluir_controles=True,
            hoy=hoy,
            fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 4: SOLO CONTROLES (Globales)
        # ==============================================================================
        self.enviar_bloque(
            titulo="Reporte Exclusivo de Controles Médicos",
            destinatarios=['fabio_saavedra@usmp.pe'],
            #destinatarios=['salud.ocupacional@ceneris.com'],
            filtro_proyectos=None, # Todos los proyectos
            incluir_emos=False,    # No enviar EMOs
            incluir_controles=True,
            hoy=hoy,
            fecha_limite=fecha_limite
        )

        self.stdout.write(self.style.SUCCESS('Proceso de alertas finalizado correctamente.'))


    def enviar_bloque(self, titulo, destinatarios, filtro_proyectos, incluir_emos, incluir_controles, hoy, fecha_limite):
        """
        Función auxiliar para filtrar, renderizar y enviar correos.
        """
        emos_por_vencer = []
        controles_por_vencer = []

        # 1. FILTRAR EMOs (Solo si se solicita)
        if incluir_emos:
            q_emos = Q(estado='Realizado', fecha_vencimiento__range=(hoy, fecha_limite)) & Q(
                trabajador__activo=True
            ) & (
                Q(trabajador__fecha_cese__isnull=True) | Q(trabajador__fecha_cese__gt=hoy)
            )
            
            if filtro_proyectos:
                # Filtrar por códigos específicos
                q_proy = Q(proyecto__codigo__in=filtro_proyectos) | \
                         Q(subproyecto__codigo__in=filtro_proyectos) | \
                         Q(trabajador__asignaciones__proyecto__codigo__in=filtro_proyectos)
                q_emos &= q_proy
            
            emos_qs = EMO.objects.filter(q_emos).select_related('trabajador', 'proyecto').distinct().order_by('fecha_vencimiento')
            
            # Calcular días
            for emo in emos_qs:
                emo.dias_restantes = (emo.fecha_vencimiento - hoy).days if emo.fecha_vencimiento else 0
                emos_por_vencer.append(emo)

        # 2. FILTRAR CONTROLES (Solo si se solicita)
        if incluir_controles:
            q_controles = Q(realizado=False, fecha_programada__range=(hoy, fecha_limite)) & Q(
                emo__trabajador__activo=True
            ) & (
                Q(emo__trabajador__fecha_cese__isnull=True) | Q(emo__trabajador__fecha_cese__gt=hoy)
            )
            
            if filtro_proyectos:
                q_proy_ctrl = Q(emo__proyecto__codigo__in=filtro_proyectos) | \
                              Q(emo__subproyecto__codigo__in=filtro_proyectos) | \
                              Q(emo__trabajador__asignaciones__proyecto__codigo__in=filtro_proyectos)
                q_controles &= q_proy_ctrl
            
            controles_qs = Control.objects.filter(q_controles).select_related('emo', 'emo__trabajador').distinct().order_by('fecha_programada')

            # Calcular días
            for ctrl in controles_qs:
                ctrl.dias_restantes = (ctrl.fecha_programada - hoy).days if ctrl.fecha_programada else 0
                controles_por_vencer.append(ctrl)

        # 3. ENVIAR SI HAY DATOS
        if emos_por_vencer or controles_por_vencer:
            context = {
                'titulo_reporte': titulo, # Variable nueva para el HTML
                'emos_por_vencer': emos_por_vencer,
                'controles_por_vencer': controles_por_vencer,
                'hoy': hoy
            }
            try:
                # Usamos el mismo template, pero le pasaremos el título dinámico
                html = render_to_string('calidad/emails/reporte_consolidado_vencimientos.html', context)
                asunto = f"⚠️ {titulo} - {hoy.strftime('%d/%m/%Y')}"
                
                msg = EmailMultiAlternatives(asunto, "Reporte adjunto en HTML.", settings.DEFAULT_FROM_EMAIL, destinatarios)
                msg.attach_alternative(html, "text/html")
                msg.send()
                self.stdout.write(f"  -> Enviado: {titulo} a {len(destinatarios)} destinatarios.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Error enviando {titulo}: {e}"))
        else:
            self.stdout.write(f"  -> Omitido: {titulo} (Sin registros pendientes).")