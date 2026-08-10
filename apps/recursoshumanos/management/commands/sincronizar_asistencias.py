# recursoshumanos/management/commands/sincronizar_asistencias.py
from django.core.management.base import BaseCommand
from recursoshumanos.servicios_asistencias import sincronizar_biometrico_fragmentado
from rest_framework.decorators import api_view

class Command(BaseCommand):
    help = 'Sincroniza asistencias del reloj biométrico'

    def add_arguments(self, parser):
        parser.add_argument('--desde', type=str, help='Fecha inicio YYYY-MM-DD (default: día 1 del mes actual)')
        parser.add_argument('--hasta', type=str, help='Fecha fin YYYY-MM-DD (default: hoy)')

    def handle(self, *args, **kwargs):
        desde = kwargs.get('desde')
        hasta = kwargs.get('hasta')
        nuevos, detalle = sincronizar_biometrico_fragmentado(con_detalle=True, desde=desde, hasta=hasta)

        self.stdout.write('--- Detalle de lectura por tabla ---')
        self.stdout.write(
            f"Rango consultado: {detalle['rango_fechas']['inicio']} a {detalle['rango_fechas']['fin']}"
        )

        self.stdout.write('Tablas de empleados:')
        for tabla, stats in detalle['empleados_tablas'].items():
            self.stdout.write(
                f"  - {tabla}: leidas={stats['filas_leidas']}, mapeadas={stats['filas_mapeadas']}"
            )

        self.stdout.write('Tablas de marcaciones:')
        for tabla, stats in detalle['marcas_tablas'].items():
            self.stdout.write(f"  - {tabla}: leidas={stats['filas_leidas']}")

        self.stdout.write('Tablas de justificaciones:')
        for tabla, stats in detalle['justificaciones']['tablas'].items():
            if stats.get('error'):
                self.stdout.write(
                    f"  - {tabla}: leidas={stats['filas_leidas']}, error={stats['error']}"
                )
            else:
                self.stdout.write(f"  - {tabla}: leidas={stats['filas_leidas']}")

        self.stdout.write(
            f"Totales: empleados mapeados={detalle['empleados_mapeados_total']}, "
            f"marcaciones leidas={detalle['marcas_total_leidas']}, "
            f"marcaciones procesadas={detalle['marcaciones_procesadas_total']}"
        )

        self.stdout.write('--- Depuracion de procesamiento ---')
        self.stdout.write(
            f"Evaluadas={detalle['marcas_evaluadas']}, validas para busqueda={detalle['marcas_validas_para_busqueda']}"
        )
        self.stdout.write(
            f"Descartes: sin_dni={detalle['descartes']['sin_mapeo_dni']}, "
            f"fecha_hora_invalida={detalle['descartes']['fecha_hora_invalida']}, "
            f"trabajador_no_encontrado={detalle['descartes']['trabajador_no_encontrado']}, "
            f"trabajador_sin_usuario={detalle['descartes']['trabajador_sin_usuario']}, "
            f"asistencia_duplicada={detalle['descartes']['asistencia_duplicada']}, "
            f"errores_inesperados={detalle['descartes']['errores_inesperados']}"
        )
        self.stdout.write(
            f"Tareo: creados={detalle['tareo']['creados']}, actualizados={detalle['tareo']['actualizados']}"
        )
        self.stdout.write('--- Depuracion de justificaciones ---')
        self.stdout.write(
            f"Leidas={detalle['justificaciones']['total_leidas']}, "
            f"evaluadas={detalle['justificaciones']['evaluadas']}, "
            f"sin_dni={detalle['justificaciones']['sin_mapeo_dni']}, "
            f"trabajador_no_encontrado={detalle['justificaciones']['trabajador_no_encontrado']}, "
            f"errores_inesperados={detalle['justificaciones']['errores_inesperados']}"
        )
        self.stdout.write(
            f"Aplicacion: tareos_creados={detalle['justificaciones']['tareos_creados']}, "
            f"tareos_marcados_j={detalle['justificaciones']['tareos_marcados_j']}, "
            f"just_locales_creadas={detalle['justificaciones']['registros_locales_creados']}, "
            f"just_locales_actualizadas={detalle['justificaciones']['registros_locales_actualizados']}"
        )

        if detalle['muestras']['codigos_sin_dni']:
            self.stdout.write(
                f"Muestra codigos sin DNI ({len(detalle['muestras']['codigos_sin_dni'])}): "
                f"{', '.join(detalle['muestras']['codigos_sin_dni'])}"
            )
        if detalle['muestras']['dnis_sin_trabajador']:
            self.stdout.write(
                f"Muestra DNI sin Trabajador ({len(detalle['muestras']['dnis_sin_trabajador'])}): "
                f"{', '.join(detalle['muestras']['dnis_sin_trabajador'])}"
            )
        if detalle['muestras']['trabajadores_sin_usuario']:
            self.stdout.write(
                f"Muestra Trabajador sin usuario ({len(detalle['muestras']['trabajadores_sin_usuario'])}): "
                f"{', '.join(detalle['muestras']['trabajadores_sin_usuario'])}"
            )
        if detalle['muestras']['errores']:
            self.stdout.write(
                f"Muestra errores ({len(detalle['muestras']['errores'])}): "
                f"{' | '.join(detalle['muestras']['errores'])}"
            )
        if detalle['muestras']['just_codigos_sin_dni']:
            self.stdout.write(
                f"Muestra JUST codigos sin DNI ({len(detalle['muestras']['just_codigos_sin_dni'])}): "
                f"{', '.join(detalle['muestras']['just_codigos_sin_dni'])}"
            )
        if detalle['muestras']['just_dnis_sin_trabajador']:
            self.stdout.write(
                f"Muestra JUST DNI sin Trabajador ({len(detalle['muestras']['just_dnis_sin_trabajador'])}): "
                f"{', '.join(detalle['muestras']['just_dnis_sin_trabajador'])}"
            )
        if detalle['muestras']['just_errores']:
            self.stdout.write(
                f"Muestra JUST errores ({len(detalle['muestras']['just_errores'])}): "
                f"{' | '.join(detalle['muestras']['just_errores'])}"
            )
        self.stdout.write(self.style.SUCCESS(f'Sincronización completa. {nuevos} marcaciones nuevas.'))