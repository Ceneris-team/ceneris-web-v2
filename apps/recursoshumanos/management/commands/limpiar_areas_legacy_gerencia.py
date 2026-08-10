from django.core.management.base import BaseCommand
from django.db import transaction

from recursoshumanos.models import Area, Trabajador


LEGACY_PREFIX = 'gerencia general'


class Command(BaseCommand):
    help = (
        'Limpia asignaciones legacy de areas con prefijo "Gerencia General". '
        'Por defecto es dry-run; usa --apply para ejecutar cambios reales.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Ejecuta los cambios en base de datos. Sin este flag es solo simulacion.',
        )
        parser.add_argument(
            '--delete-areas',
            action='store_true',
            help='Elimina los registros de Area legacy luego de limpiar asignaciones.',
        )

    def _es_area_legacy(self, nombre):
        return (nombre or '').strip().lower().startswith(LEGACY_PREFIX)

    def _inferir_area_destino(self, area_legacy, areas_no_legacy_por_nombre):
        nombre = (area_legacy.nombre or '').strip()
        candidato = None

        if '/' in nombre:
            candidato = nombre.split('/')[-1].strip()
        elif '-' in nombre:
            candidato = nombre.split('-')[-1].strip()

        if not candidato:
            return None

        return areas_no_legacy_por_nombre.get(candidato.lower())

    def handle(self, *args, **options):
        aplicar = options['apply']
        borrar_areas = options['delete_areas']

        areas_legacy = list(Area.objects.filter(nombre__istartswith='Gerencia General').order_by('nombre'))
        if not areas_legacy:
            self.stdout.write(self.style.SUCCESS('No se encontraron areas legacy para limpiar.'))
            return

        legacy_ids = [a.id for a in areas_legacy]
        legacy_por_id = {a.id: a for a in areas_legacy}

        areas_no_legacy = Area.objects.exclude(id__in=legacy_ids)
        areas_no_legacy_por_nombre = {a.nombre.strip().lower(): a for a in areas_no_legacy}

        mapeo_destino = {}
        for area in areas_legacy:
            destino = self._inferir_area_destino(area, areas_no_legacy_por_nombre)
            if destino:
                mapeo_destino[area.id] = destino

        trabajadores_fk_qs = Trabajador.objects.filter(area_id__in=legacy_ids).order_by('id')
        through = Trabajador.areas_supervisadas.through
        asignaciones_m2m_qs = through.objects.filter(area_id__in=legacy_ids).order_by('id')

        self.stdout.write(self.style.WARNING('=== RESUMEN PREVIO (DRY-RUN) ==='))
        self.stdout.write(f'Areas legacy detectadas: {len(areas_legacy)}')
        for area in areas_legacy:
            destino = mapeo_destino.get(area.id)
            destino_txt = destino.nombre if destino else 'SIN MAPEO (quedara null/removido)'
            self.stdout.write(f'- {area.id}: {area.nombre} -> {destino_txt}')

        self.stdout.write(f'Trabajadores con area FK legacy: {trabajadores_fk_qs.count()}')
        self.stdout.write(f'Asignaciones M2M legacy (areas_supervisadas): {asignaciones_m2m_qs.count()}')

        if not aplicar:
            self.stdout.write(
                self.style.WARNING('No se aplicaron cambios. Ejecuta con --apply para persistir limpieza.')
            )
            return

        fk_reasignados = 0
        fk_limpiados = 0
        m2m_reasignados = 0
        m2m_limpiados = 0

        with transaction.atomic():
            for trabajador in trabajadores_fk_qs.select_related('area'):
                destino = mapeo_destino.get(trabajador.area_id)
                if destino:
                    trabajador.area_id = destino.id
                    fk_reasignados += 1
                else:
                    trabajador.area_id = None
                    fk_limpiados += 1
                trabajador.save(update_fields=['area'])

            for rel in asignaciones_m2m_qs:
                destino = mapeo_destino.get(rel.area_id)
                if destino:
                    existe = through.objects.filter(
                        trabajador_id=rel.trabajador_id,
                        area_id=destino.id,
                    ).exists()
                    if not existe:
                        through.objects.create(
                            trabajador_id=rel.trabajador_id,
                            area_id=destino.id,
                        )
                        m2m_reasignados += 1

                rel.delete()
                m2m_limpiados += 1

            areas_eliminadas = 0
            if borrar_areas:
                areas_eliminadas, _ = Area.objects.filter(id__in=legacy_ids).delete()

        self.stdout.write(self.style.SUCCESS('=== LIMPIEZA APLICADA ==='))
        self.stdout.write(f'FK reasignados a area real: {fk_reasignados}')
        self.stdout.write(f'FK limpiados a null: {fk_limpiados}')
        self.stdout.write(f'M2M reasignados a area real: {m2m_reasignados}')
        self.stdout.write(f'M2M legacy removidos: {m2m_limpiados}')
        if borrar_areas:
            self.stdout.write(f'Registros Area eliminados: {areas_eliminadas}')
