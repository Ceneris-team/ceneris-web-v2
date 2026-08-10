# recursoshumanos/management/commands/recalcular_tareos.py
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from recursoshumanos.models import TareoDiario
from recursoshumanos.services import recalcular_asistencia_diaria


class Command(BaseCommand):
    help = (
        'Recalcula el TareoDiario (resultado, horas de entrada/salida y tardanza) '
        'a partir de las marcaciones reales ya guardadas en Asistencia. Sirve '
        'cuando se cargaron marcaciones por fuera del flujo normal (SQL directo, '
        'importaciones, etc.) y el dia quedo como Falta pese a tener marcas. '
        'Los dias justificados (J) no se tocan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--desde', type=str,
            help='Fecha inicio YYYY-MM-DD (default: primer dia del mes actual)',
        )
        parser.add_argument(
            '--hasta', type=str,
            help='Fecha fin YYYY-MM-DD (default: hoy)',
        )
        parser.add_argument(
            '--dni', type=str,
            help='Limitar a un solo trabajador por DNI',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra que cambiaria, sin guardar nada en la base de datos',
        )

    def handle(self, *args, **options):
        hoy = timezone.localdate()

        try:
            desde = (
                datetime.date.fromisoformat(options['desde'])
                if options.get('desde') else hoy.replace(day=1)
            )
            hasta = (
                datetime.date.fromisoformat(options['hasta'])
                if options.get('hasta') else hoy
            )
        except ValueError:
            raise CommandError('Formato de fecha invalido. Usa YYYY-MM-DD.')

        if desde > hasta:
            raise CommandError('La fecha --desde no puede ser posterior a --hasta.')

        dry_run = options.get('dry_run')

        qs = (TareoDiario.objects
              .filter(fecha__gte=desde, fecha__lte=hasta)
              .select_related('trabajador')
              .order_by('fecha', 'trabajador__apellido_paterno'))

        if options.get('dni'):
            qs = qs.filter(trabajador__dni=options['dni'])

        self.stdout.write(f'Rango: {desde} a {hasta}')
        if options.get('dni'):
            self.stdout.write(f'Trabajador: DNI {options["dni"]}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: no se guardara ningun cambio.'))
        self.stdout.write(f'Tareos a revisar: {qs.count()}')
        self.stdout.write('-' * 100)

        cambiados = 0
        sin_cambios = 0

        with transaction.atomic():
            for tareo in qs:
                antes = (
                    tareo.resultado,
                    tareo.hora_entrada_real,
                    tareo.hora_salida_real,
                    tareo.horas_tardanza,
                )

                # Si el dia no tiene marcaciones, la funcion retorna sin tocar nada.
                recalcular_asistencia_diaria(tareo)
                tareo.refresh_from_db()

                despues = (
                    tareo.resultado,
                    tareo.hora_entrada_real,
                    tareo.hora_salida_real,
                    tareo.horas_tardanza,
                )

                if antes == despues:
                    sin_cambios += 1
                    continue

                cambiados += 1
                self.stdout.write(
                    f'{tareo.fecha} | {tareo.trabajador.nombre_completo}\n'
                    f'    antes:   resultado={antes[0]} entrada={antes[1]} salida={antes[2]} tardanza={antes[3]}\n'
                    f'    despues: resultado={despues[0]} entrada={despues[1]} salida={despues[2]} tardanza={despues[3]}'
                )

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write('-' * 100)
        self.stdout.write(f'Sin cambios: {sin_cambios}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Cambiarian: {cambiados} (NO se guardo nada, fue un dry-run)'
            ))
            self.stdout.write('Volve a correr el comando sin --dry-run para aplicar los cambios.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Actualizados: {cambiados}'))
