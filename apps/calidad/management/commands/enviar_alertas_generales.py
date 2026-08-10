from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from calidad.models import EMO, Control

class Command(BaseCommand):
    help = 'Envía alertas de vencimientos segmentadas por proyecto, empresa y permisos de visualización'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando proceso de alertas masivas...")
        
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=30) # Anticipación de un mes

        # --- DEFINICIÓN DE CÓDIGOS ---
        codigos_antapaccay = ['PRO-ANT-HIDRO', 'PRO-CMA']
        codigos_cerro_verde = ['PRO-CV', 'PRO-SMCV', 'CVERDE']
        # Lista para excluir estos proyectos del reporte general
        proyectos_excluidos_global = codigos_antapaccay + codigos_cerro_verde

        # ==============================================================================
        # GRUPO 1: ANTAPACCAY (2 Correos Diferentes)
        # ==============================================================================
        
        # 1.A: RESTRINGIDO (Para Admin/RRHH - No ven detalles médicos)
        self.enviar_bloque(
            titulo="Reporte Vencimientos Compañia Minera Antapaccay",
            destinatarios=['ingenierohse.cma@ceneris.com','ssoma@ceneris.com','consultor03@ceneris.com','habilitaciones@ceneris.com','fabio_saavedra@usmp.pe'],
            filtro_proyectos=codigos_antapaccay,
            ocultar_detalle=True,
            hoy=hoy, fecha_limite=fecha_limite
        )

        # 1.B: COMPLETO (Para Doctores - Ven todo)
        self.enviar_bloque(
            titulo="Reporte Vencimientos Compañia Minera Antapaccay",
            destinatarios=['salud.ocupacional@ceneris.com'], # Aquí iría el correo del doctor
            filtro_proyectos=codigos_antapaccay,
            ocultar_detalle=False, # <--- SE MUESTRA EL DETALLE
            hoy=hoy, fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 2: CERRO VERDE (2 Correos Diferentes)
        # ==============================================================================
        
        # 2.A: RESTRINGIDO
        self.enviar_bloque(
            titulo="Reporte Vencimientos Sociedad Minera Cerro Verde",
            destinatarios=['consultor01@ceneris.com', 'consultor02@ceneris.com','consultor04@ceneris.com','smcv.ceneris@ceneris.com','habilitaciones@ceneris.com','fabio_saavedra@usmp.pe'],
            filtro_proyectos=codigos_cerro_verde,
            ocultar_detalle=True,
            hoy=hoy, fecha_limite=fecha_limite
        )

        # 2.B: COMPLETO
        self.enviar_bloque(
            titulo="Reporte Vencimientos Sociedad Minera Cerro Verde",
            destinatarios=['salud.ocupacional@ceneris.com'], # Aquí iría el doctor de CV
            filtro_proyectos=codigos_cerro_verde,
            ocultar_detalle=False,
            hoy=hoy, fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 3: RESTO DE PROYECTOS (Global - Excluyendo los anteriores)
        # ==============================================================================
        self.enviar_bloque(
            titulo="Reporte Vencimientos - PROYECTOS VARIOS",
            destinatarios=['salud.ocupacional@ceneris.com', 'habilitaciones@ceneris.com'],
            filtro_proyectos=None,
            excluir_proyectos=proyectos_excluidos_global,
            ocultar_detalle=False, 
            hoy=hoy, fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 4: SOLO CONTROLES (De todos los proyectos)
        # ==============================================================================
        self.enviar_bloque(
            titulo="Reporte General de Controles Médicos",
            destinatarios=['salud.ocupacional@ceneris.com'], # Idealmente salud.ocupacional@ceneris.com
            filtro_proyectos=None,
            incluir_emos=False,     # <--- Solo controles
            incluir_controles=True,
            ocultar_detalle=False,  # Salud ocupacional debe ver el detalle
            hoy=hoy, fecha_limite=fecha_limite
        )

        # ==============================================================================
        # GRUPO 5: METRALAB Y GLOBAL GROUP (Filtro por Empresa)
        # ==============================================================================
        # esto filtra los emos segun empresa del trabajador, mas no de la empresa del emo.
        nombres_empresas = ['METRALAB S.A.C.', 'GLOBAL GROUP S.A.C.']
        
        self.enviar_bloque(
            titulo="Reporte Vencimientos trabajadores de METRALAB y GLOBAL GROUP",
            destinatarios=['salud.ocupacional@ceneris.com','habilitaciones@ceneris.com'],
            filtro_proyectos=None, 
            filtro_empresas=nombres_empresas, # Filtro específico por nombre de empresa
            incluir_emos=True,
            incluir_controles=True,
            hoy=hoy, fecha_limite=fecha_limite
        )

        self.stdout.write(self.style.SUCCESS('Proceso de alertas finalizado correctamente.'))


    def enviar_bloque(self, titulo, destinatarios, hoy, fecha_limite, 
                      filtro_proyectos=None, excluir_proyectos=None, 
                      filtro_empresas=None, incluir_emos=True, incluir_controles=True, 
                      ocultar_detalle=False):
        """
        Función auxiliar inteligente para filtrar, renderizar y enviar correos.
        """
        emos_por_vencer = []
        controles_por_vencer = []

        # --- 1. LÓGICA DE EMOs ---
        if incluir_emos:
            q_emos = Q(estado='Realizado', fecha_vencimiento__range=(hoy, fecha_limite)) & Q(
                trabajador__activo=True
            ) & (
                Q(trabajador__fecha_cese__isnull=True) | Q(trabajador__fecha_cese__gt=hoy)
            )
            
            # Filtro INCLUSIVO (Solo estos proyectos)
            if filtro_proyectos:
                q_emos &= (
                    Q(proyecto__codigo__in=filtro_proyectos) | 
                    Q(subproyecto__codigo__in=filtro_proyectos) |
                    Q(trabajador__asignaciones__proyecto__codigo__in=filtro_proyectos)
                )

            # Filtro de EMPRESA
            if filtro_empresas:
                q_emos &= (
                    Q(empresa__nombre__in=filtro_empresas) | 
                    Q(trabajador__empresa__nombre__in=filtro_empresas)
                )
            
            # Filtro EXCLUSIVO (Todos MENOS estos proyectos)
            if excluir_proyectos:
                q_emos &= ~(
                    Q(proyecto__codigo__in=excluir_proyectos) | 
                    Q(subproyecto__codigo__in=excluir_proyectos) |
                    Q(trabajador__asignaciones__proyecto__codigo__in=excluir_proyectos)
                )

            emos_qs = EMO.objects.filter(q_emos).select_related('trabajador', 'proyecto').distinct().order_by('fecha_vencimiento')
            for emo in emos_qs:
                emo.dias_restantes = (emo.fecha_vencimiento - hoy).days if emo.fecha_vencimiento else 0
                emos_por_vencer.append(emo)

        # --- 2. LÓGICA DE CONTROLES ---
        if incluir_controles:
            q_controles = Q(realizado=False, fecha_programada__range=(hoy, fecha_limite)) & Q(
                emo__trabajador__activo=True
            ) & (
                Q(emo__trabajador__fecha_cese__isnull=True) | Q(emo__trabajador__fecha_cese__gt=hoy)
            )

            # Filtro por Proyecto
            if filtro_proyectos:
                q_controles &= (
                    Q(emo__proyecto__codigo__in=filtro_proyectos) | 
                    Q(emo__subproyecto__codigo__in=filtro_proyectos) |
                    Q(emo__trabajador__asignaciones__proyecto__codigo__in=filtro_proyectos)
                )

            # Filtro por Empresa
            if filtro_empresas:
                q_controles &= (
                    Q(emo__empresa__nombre__in=filtro_empresas) | 
                    Q(emo__trabajador__empresa__nombre__in=filtro_empresas)
                )
            
            # Filtro Exclusivo
            if excluir_proyectos:
                q_controles &= ~(
                    Q(emo__proyecto__codigo__in=excluir_proyectos) | 
                    Q(emo__subproyecto__codigo__in=excluir_proyectos) |
                    Q(emo__trabajador__asignaciones__proyecto__codigo__in=excluir_proyectos)
                )

            controles_qs = Control.objects.filter(q_controles).select_related('emo', 'emo__trabajador').distinct().order_by('fecha_programada')
            for ctrl in controles_qs:
                ctrl.dias_restantes = (ctrl.fecha_programada - hoy).days if ctrl.fecha_programada else 0
                controles_por_vencer.append(ctrl)

        # --- 3. ENVÍO ---
        if emos_por_vencer or controles_por_vencer:
            context = {
                'titulo_reporte': titulo,
                'emos_por_vencer': emos_por_vencer,
                'controles_por_vencer': controles_por_vencer,
                'ocultar_detalle': ocultar_detalle, # Variable clave para el HTML
                'hoy': hoy
            }
            try:
                html = render_to_string('calidad/emails/reporte_consolidado_vencimientos.html', context)
                asunto = f"⚠️ {titulo} - {hoy.strftime('%d/%m')}"
                
                msg = EmailMultiAlternatives(asunto, "Reporte adjunto.", settings.DEFAULT_FROM_EMAIL, destinatarios)
                msg.attach_alternative(html, "text/html")
                msg.send()
                self.stdout.write(f"  -> Enviado: {titulo} ({len(destinatarios)} destinatarios)")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Error {titulo}: {e}"))
        else:
            self.stdout.write(f"  -> Omitido: {titulo} (Vacío)")