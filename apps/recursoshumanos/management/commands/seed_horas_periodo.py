# recursoshumanos/management/commands/seed_horas_periodo.py
"""Datos de prueba para el reporte de Horas Acumuladas por Período.

Crea 12 trabajadores con la ficha completa (empresa, sede, área, cargo, centro
de costo, proyecto, datos personales) y su tareo día a día en el rango pedido,
con perfiles horarios distintos para poder ver el reporte con casos reales:
jornada completa, media jornada de practicante, turno de campo, faltas, días
libres y marcaciones incompletas.

Es solo para desarrollo local. Los trabajadores se reconocen por un rango de
DNI reservado (825000xx) para no tocar los reales, y `--limpiar` los borra.
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from recursoshumanos.models import (
    Area,
    Cargo,
    CentroCosto,
    Empresa,
    Proyecto,
    Sede,
    TareoDiario,
    Trabajador,
    Ubicacion,
)
from recursoshumanos.motor_reglas import EstadoMarca

# Los trabajadores de prueba viven en este rango de DNI. Nada fuera de él se
# toca nunca, ni al crear ni al limpiar.
PREFIJO_DNI = '8250'

# Perfiles horarios. `horas` es lo que se guarda en horas_trabajadas_validas y
# ya viene con la regla de almuerzo aplicada: se resta 1 h cuando la jornada
# pasa de 5 h, igual que hace services.recalcular_asistencia_diaria.
PERFILES = {
    'oficina':     {'entrada': datetime.time(8, 30),  'salida': datetime.time(18, 0),  'horas': Decimal('8.50'), 'estado': 'O'},
    'campo':       {'entrada': datetime.time(7, 0),   'salida': datetime.time(17, 0),  'horas': Decimal('9.00'), 'estado': 'C'},
    'practicante': {'entrada': datetime.time(8, 30),  'salida': datetime.time(13, 0),  'horas': Decimal('4.50'), 'estado': 'O'},
    'tarde':       {'entrada': datetime.time(14, 0),  'salida': datetime.time(22, 0),  'horas': Decimal('7.00'), 'estado': 'O'},
}

# (dni_sufijo, apellido_paterno, apellido_materno, nombres, sexo, area, cargo,
#  perfil, incidencia)
#
# `incidencia` inyecta un caso especial en el período para que el reporte no
# salga plano:
#   'sin_salida'  -> un día marcó entrada y nunca salida: suma 0 h y dispara ⚠️
#   'falta'       -> un día sin ninguna marca estando programado
#   'libre_extra' -> un día libre entre semana (no cuenta como día esperado)
#   'tardanza'    -> entró tarde: menos horas ese día
#   None          -> asistencia limpia
PERSONAL = [
    ('01', 'Quispe',   'Mamani',   'Carlos Alberto', 'M', 'Operaciones',  'Supervisor de Campo',   'campo',       None),
    ('02', 'Huamani',  'Ccopa',    'Rosa Elena',     'F', 'Operaciones',  'Operario de Campo',     'campo',       'tardanza'),
    ('03', 'Torres',   'Salazar',  'Luis Fernando',  'M', 'Operaciones',  'Operario de Campo',     'campo',       'sin_salida'),
    ('04', 'Vargas',   'Rojas',    'Maria Cristina', 'F', 'Administracion', 'Asistente Administrativo', 'oficina', None),
    ('05', 'Flores',   'Apaza',    'Jorge Enrique',  'M', 'Administracion', 'Analista de Costos',  'oficina',     'falta'),
    ('06', 'Condori',  'Chura',    'Ana Lucia',      'F', 'Administracion', 'Coordinadora de RRHH', 'oficina',    None),
    ('07', 'Ramirez',  'Pacheco',  'Diego Martin',   'M', 'Calidad',      'Inspector de Calidad',  'oficina',     'libre_extra'),
    ('08', 'Gutierrez', 'Nina',    'Patricia Isabel', 'F', 'Calidad',     'Inspectora de Calidad', 'tarde',       None),
    ('09', 'Mendoza',  'Sulca',    'Andres Felipe',  'M', 'Calidad',      'Practicante de Calidad', 'practicante', None),
    ('10', 'Cabrera',  'Yupanqui', 'Sofia Alejandra', 'F', 'Administracion', 'Practicante de RRHH', 'practicante', None),
    ('11', 'Ochoa',    'Tello',    'Ricardo Manuel', 'M', 'Operaciones',  'Practicante de Campo',  'practicante', 'sin_salida'),
    ('12', 'Palomino', 'Arce',     'Elena Beatriz',  'F', 'Administracion', 'Jefa de Administracion', 'oficina',  None),
]


class Command(BaseCommand):
    help = (
        'Crea trabajadores y tareo de prueba para el reporte de Horas Acumuladas '
        'por Periodo. Solo para desarrollo local.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--desde', type=str,
            help='Fecha inicio YYYY-MM-DD (default: hace 30 dias)',
        )
        parser.add_argument(
            '--hasta', type=str,
            help='Fecha fin YYYY-MM-DD (default: ayer)',
        )
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Borra los trabajadores de prueba (DNI 8250xxxx) y su tareo, sin crear nada.',
        )

    def handle(self, *args, **opciones):
        if opciones['limpiar']:
            return self._limpiar()

        hoy = timezone.localdate()
        desde = self._fecha(opciones['desde']) or hoy - datetime.timedelta(days=30)
        hasta = self._fecha(opciones['hasta']) or hoy - datetime.timedelta(days=1)

        if desde > hasta:
            raise CommandError('--desde no puede ser posterior a --hasta.')
        if hasta > hoy:
            self.stdout.write(self.style.WARNING(
                'El reporte recorta los dias futuros; se generara tareo solo hasta hoy.'
            ))
            hasta = hoy

        with transaction.atomic():
            catalogos = self._crear_catalogos()
            trabajadores = self._crear_trabajadores(catalogos)
            dias = self._crear_tareos(trabajadores, desde, hasta)

        self.stdout.write(self.style.SUCCESS(
            '\nListo: %d trabajadores y %d dias de tareo entre %s y %s.'
            % (len(trabajadores), dias, desde, hasta)
        ))
        self.stdout.write(
            '\nAbre el reporte en /recursoshumanos/reportes/horas-periodo/ '
            'con Desde=%s y Hasta=%s.' % (desde, hasta)
        )
        self.stdout.write(
            'Para borrarlos: manage.py seed_horas_periodo --limpiar'
        )

    # -- helpers ------------------------------------------------------------

    def _fecha(self, valor):
        if not valor:
            return None
        try:
            return datetime.datetime.strptime(valor, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError('Fecha invalida: %s. Usa YYYY-MM-DD.' % valor)

    def _limpiar(self):
        qs = Trabajador.objects.filter(dni__startswith=PREFIJO_DNI)
        total = qs.count()
        if not total:
            self.stdout.write('No hay trabajadores de prueba que borrar.')
            return
        tareos = TareoDiario.objects.filter(trabajador__in=qs).count()
        qs.delete()  # el tareo cae por CASCADE
        self.stdout.write(self.style.SUCCESS(
            'Borrados %d trabajadores de prueba y %d dias de tareo.' % (total, tareos)
        ))

    def _crear_catalogos(self):
        empresa, _ = Empresa.objects.get_or_create(
            nombre='Ceneris Demo S.A.C.',
            defaults={
                'ruc': '20600000001',
                'direccion': 'Av. Ejercito 710, Yanahuara, Arequipa',
                'telefono': '054-200100',
                'email_contacto': 'contacto@ceneris-demo.pe',
                'persona_contacto': 'Elena Palomino',
            },
        )
        sede, _ = Sede.objects.get_or_create(
            nombre='Sede Arequipa',
            defaults={'direccion': 'Parque Industrial Rio Seco, Cerro Colorado', 'activo': True},
        )
        centro, _ = CentroCosto.objects.get_or_create(
            codigo='K400', defaults={'nombre': 'Operaciones Mina'},
        )
        ubicacion, _ = Ubicacion.objects.get_or_create(
            nombre='Planta Rio Seco',
            defaults={
                'hora_entrada': datetime.time(8, 0),
                'latitud': -16.3606, 'longitud': -71.5731, 'radio': 150,
            },
        )
        proyecto, _ = Proyecto.objects.get_or_create(
            nombre='Monitoreo Ambiental 2026',
            defaults={
                'codigo': 'PRY-2026-01', 'empresa': empresa,
                'cliente': 'Southern Peru', 'fecha_inicio': datetime.date(2026, 1, 15),
                'activo': True,
            },
        )

        areas = {}
        for nombre, codigo in (('Operaciones', 'OPE'), ('Administracion', 'ADM'), ('Calidad', 'CAL')):
            areas[nombre], _ = Area.objects.get_or_create(
                nombre=nombre,
                defaults={'codigo': codigo, 'descripcion': 'Area %s' % nombre},
            )

        # El catalogo de cargos esta vacio en limpio; se puebla con los que usa
        # este seed para que el desplegable de la ficha del trabajador sirva.
        for indice, nombre in enumerate(sorted({fila[6] for fila in PERSONAL}), start=1):
            Cargo.objects.get_or_create(
                nombre=nombre, defaults={'codigo': 'C%03d' % indice},
            )

        self.stdout.write('Catalogos listos: empresa, sede, 3 areas, centro de costo, ubicacion, proyecto y cargos.')
        return {
            'empresa': empresa, 'sede': sede, 'centro': centro,
            'ubicacion': ubicacion, 'proyecto': proyecto, 'areas': areas,
        }

    def _crear_trabajadores(self, catalogos):
        hoy = timezone.localdate()
        creados = []

        for indice, fila in enumerate(PERSONAL):
            sufijo, paterno, materno, nombres, sexo, area, cargo, perfil, incidencia = fila
            dni = PREFIJO_DNI + '00' + sufijo

            trabajador, nuevo = Trabajador.objects.update_or_create(
                dni=dni,
                defaults={
                    'apellido_paterno': paterno,
                    'apellido_materno': materno,
                    'nombres': nombres,
                    'empresa': catalogos['empresa'],
                    'sede': catalogos['sede'],
                    'area': catalogos['areas'][area],
                    'centro_costo': catalogos['centro'],
                    'cargo': cargo,
                    'fecha_ingreso': hoy - datetime.timedelta(days=365 + indice * 40),
                    'fecha_nacimiento': datetime.date(1985 + indice, (indice % 12) + 1, (indice % 27) + 1),
                    'sexo': sexo,
                    'email': '%s.%s@ceneris-demo.pe' % (nombres.split()[0].lower(), paterno.lower()),
                    'telefono': '9%08d' % (51000000 + indice),
                    'es_jefe': cargo.startswith(('Jefa', 'Jefe', 'Supervisor', 'Coordinadora')),
                    'es_gerente': False,
                    'activo': True,
                },
            )
            trabajador.ubicaciones_permitidas.add(catalogos['ubicacion'])
            trabajador.asignaciones.get_or_create(
                proyecto=catalogos['proyecto'],
                defaults={
                    'cargo': Cargo.objects.filter(nombre=cargo).first(),
                    'fecha_inicio': trabajador.fecha_ingreso,
                    'activo': True,
                },
            )
            creados.append((trabajador, perfil, incidencia))
            self.stdout.write('  %s %s %s, %s (%s / %s)' % (
                '+' if nuevo else '=', dni, paterno, nombres, area, cargo,
            ))

        return creados

    def _crear_tareos(self, trabajadores, desde, hasta):
        # Se reemplaza el tareo del rango para poder reejecutar el comando sin
        # duplicar dias ni arrastrar una corrida anterior.
        TareoDiario.objects.filter(
            trabajador__in=[t for t, _, _ in trabajadores],
            fecha__gte=desde, fecha__lte=hasta,
        ).delete()

        dias_habiles = [
            desde + datetime.timedelta(days=n)
            for n in range((hasta - desde).days + 1)
            if (desde + datetime.timedelta(days=n)).weekday() < 5
        ]
        if not dias_habiles:
            raise CommandError('El rango no tiene ningun dia habil.')

        # La incidencia cae siempre en el mismo dia habil para que el reporte
        # sea reproducible entre corridas.
        dia_incidencia = dias_habiles[len(dias_habiles) // 2]

        nuevos = []
        for trabajador, nombre_perfil, incidencia in trabajadores:
            perfil = PERFILES[nombre_perfil]
            fecha = desde
            while fecha <= hasta:
                nuevos.append(self._tareo_del_dia(
                    trabajador, fecha, perfil, incidencia, dia_incidencia,
                ))
                fecha += datetime.timedelta(days=1)

        TareoDiario.objects.bulk_create(nuevos)
        return len(nuevos)

    def _tareo_del_dia(self, trabajador, fecha, perfil, incidencia, dia_incidencia):
        # Fin de semana: dia libre. No cuenta como dia esperado ni penaliza.
        if fecha.weekday() >= 5:
            return TareoDiario(
                trabajador=trabajador, fecha=fecha, estado='D', resultado='A',
                horas_trabajadas_validas=Decimal('0.00'),
                etiqueta_estado=EstadoMarca.DIA_LIBRE,
                detalle_marca='Fin de semana',
            )

        base = dict(
            trabajador=trabajador, fecha=fecha, estado=perfil['estado'],
            hora_entrada=perfil['entrada'], hora_salida=perfil['salida'],
        )

        if fecha == dia_incidencia and incidencia == 'sin_salida':
            # Marco entrada y nunca salida: sin par Entrada->Salida el dia suma
            # 0 h y el reporte lo señala con ⚠️.
            return TareoDiario(
                **base, resultado='A',
                hora_entrada_real=perfil['entrada'], hora_salida_real=None,
                horas_trabajadas_validas=Decimal('0.00'),
                etiqueta_estado=EstadoMarca.FUERA_DE_HORARIO,
                detalle_marca='Marco entrada sin salida registrada',
            )

        if fecha == dia_incidencia and incidencia == 'falta':
            return TareoDiario(
                **base, resultado='F',
                hora_entrada_real=None, hora_salida_real=None,
                horas_trabajadas_validas=Decimal('0.00'),
                etiqueta_estado=EstadoMarca.FALTA,
                detalle_marca='No registro marcacion',
            )

        if fecha == dia_incidencia and incidencia == 'libre_extra':
            return TareoDiario(
                trabajador=trabajador, fecha=fecha, estado='D', resultado='A',
                horas_trabajadas_validas=Decimal('0.00'),
                etiqueta_estado=EstadoMarca.DIA_LIBRE,
                detalle_marca='Dia libre compensatorio',
            )

        if fecha == dia_incidencia and incidencia == 'tardanza':
            entrada_tarde = self._sumar_minutos(perfil['entrada'], 35)
            return TareoDiario(
                **base, resultado='A',
                hora_entrada_real=entrada_tarde, hora_salida_real=perfil['salida'],
                horas_trabajadas_validas=perfil['horas'] - Decimal('0.58'),
                horas_tardanza=Decimal('0.58'),
                etiqueta_estado=EstadoMarca.TARDANZA,
                detalle_marca='Tardanza de 35 min',
            )

        return TareoDiario(
            **base, resultado='A',
            hora_entrada_real=perfil['entrada'], hora_salida_real=perfil['salida'],
            horas_trabajadas_validas=perfil['horas'],
            etiqueta_estado=EstadoMarca.NORMAL,
            detalle_marca='Asistencia completa',
        )

    def _sumar_minutos(self, hora, minutos):
        base = datetime.datetime.combine(datetime.date(2000, 1, 1), hora)
        return (base + datetime.timedelta(minutes=minutos)).time()
