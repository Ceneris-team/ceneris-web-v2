# recursoshumanos/management/commands/seed_demo.py
"""Set de datos de prueba de proposito general para desarrollo local.

Crea un catalogo completo (empresa, sede, areas, cargos, centro de costo,
ubicacion, proyecto) y 15 trabajadores con jerarquia real (gerente, jefes,
resto de personal), cada uno con su Usuario de login para poder probar la
app movil y el panel admin. Sobre eso genera:

  - Tareo diario de los ultimos 14 dias habiles, con perfiles de horario
    distintos y algunas incidencias (tardanza, falta, sin salida, dia libre
    extra) para que los reportes no salgan planos.
  - Marcaciones (Asistencia) reales para los dias con resultado "Asistio",
    consistentes con el tareo, para poblar el registro en tiempo real.
  - Una Justificacion pendiente sobre el dia de falta.
  - Solicitudes de horas extra en distintos estados del flujo de aprobacion.
  - Un par de Sanciones.

Es solo para desarrollo local. Todo el personal de prueba vive en el rango
de DNI reservado 7799xxxx para no tocar datos reales; `--limpiar` lo borra
por completo (incluyendo los Usuarios de login creados).
"""
import datetime
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from recursoshumanos.models import (
    Area,
    Asistencia,
    Cargo,
    CentroCosto,
    Empresa,
    Justificacion,
    Proyecto,
    Sancion,
    Sede,
    SolicitudHorasExtra,
    TareoDiario,
    Trabajador,
    Ubicacion,
)
from recursoshumanos.motor_reglas import EstadoMarca

User = get_user_model()

# Rango de DNI reservado para este seed. Nada fuera de el se toca nunca.
PREFIJO_DNI = '7799'
PASSWORD_DEMO = 'Demo12345'

PERFILES = {
    'oficina':     {'entrada': datetime.time(8, 30), 'salida': datetime.time(18, 0), 'horas': Decimal('8.50'), 'estado': 'O'},
    'campo':       {'entrada': datetime.time(7, 0),  'salida': datetime.time(17, 0), 'horas': Decimal('9.00'), 'estado': 'C'},
    'practicante': {'entrada': datetime.time(8, 30), 'salida': datetime.time(13, 0), 'horas': Decimal('4.50'), 'estado': 'O'},

}

# (sufijo, paterno, materno, nombres, sexo, area, cargo, perfil, es_jefe, es_gerente, incidencia)
PERSONAL = [
    ('01', 'Salazar',  'Delgado', 'Fabricio Andres',  'M', 'Administracion', 'Gerente General',        'oficina',     False, True,  None),
    ('02', 'Quispe',   'Mamani',  'Carlos Alberto',    'M', 'Operaciones',    'Jefe de Operaciones',    'campo',       True,  False, None),
    ('03', 'Palomino', 'Arce',    'Elena Beatriz',     'F', 'Administracion', 'Jefa de Administracion', 'oficina',     True,  False, None),
    ('04', 'Huamani',  'Ccopa',   'Rosa Elena',        'F', 'Operaciones',    'Supervisora de Campo',   'campo',       False, False, 'tardanza'),
    ('05', 'Torres',   'Salazar', 'Luis Fernando',     'M', 'Operaciones',    'Operario de Campo',      'campo',       False, False, 'sin_salida'),
    ('06', 'Vargas',   'Rojas',   'Maria Cristina',    'F', 'Operaciones',    'Operario de Campo',      'campo',       False, False, None),
    ('07', 'Flores',   'Apaza',   'Jorge Enrique',     'M', 'Administracion', 'Analista de Costos',     'oficina',     False, False, 'falta'),
    ('08', 'Condori',  'Chura',   'Ana Lucia',         'F', 'Administracion', 'Asistente Administrativo', 'oficina',   False, False, None),
    ('09', 'Ramirez',  'Pacheco', 'Diego Martin',      'M', 'Calidad',        'Inspector de Calidad',   'oficina',     False, False, 'libre_extra'),
    ('10', 'Gutierrez', 'Nina',   'Patricia Isabel',   'F', 'Calidad',        'Inspectora de Calidad',  'oficina',     False, False, None),
    ('11', 'Mendoza',  'Sulca',   'Andres Felipe',     'M', 'Calidad',        'Practicante de Calidad', 'practicante', False, False, None),
    ('12', 'Cabrera',  'Yupanqui', 'Sofia Alejandra',  'F', 'Recursos Humanos', 'Coordinadora de RRHH', 'oficina',     False, False, None),
    ('13', 'Ochoa',    'Tello',   'Ricardo Manuel',    'M', 'Recursos Humanos', 'Practicante de RRHH',  'practicante', False, False, None),
    ('14', 'Nina',     'Choque',  'Katherine Milagros', 'F', 'Operaciones',   'Operario de Campo',      'campo',       False, False, None),
    ('15', 'Chura',    'Apaza',   'Miguel Angel',      'M', 'Administracion', 'Asistente Administrativo', 'oficina',   False, False, None),
]


class Command(BaseCommand):
    help = (
        'Crea un set de datos de prueba de proposito general (empresa, personal, '
        'tareo, asistencias, solicitudes de horas extra, justificaciones y '
        'sanciones) para desarrollo local.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias', type=int, default=14,
            help='Cantidad de dias hacia atras (desde ayer) para generar tareo. Default: 14.',
        )
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Borra todos los datos de prueba (DNI 7799xxxx) y sus Usuarios de login, sin crear nada.',
        )

    def handle(self, *args, **opciones):
        if opciones['limpiar']:
            return self._limpiar()

        dias = opciones['dias']
        if dias < 1:
            raise CommandError('--dias debe ser al menos 1.')

        hoy = timezone.localdate()
        hasta = hoy - datetime.timedelta(days=1)
        desde = hasta - datetime.timedelta(days=dias - 1)

        with transaction.atomic():
            catalogos = self._crear_catalogos()
            trabajadores = self._crear_trabajadores(catalogos)
            dias_creados = self._crear_tareos_y_asistencias(trabajadores, desde, hasta)
            self._crear_justificacion(trabajadores)
            self._crear_solicitudes_horas_extra(trabajadores)
            self._crear_sanciones(trabajadores)

        self.stdout.write(self.style.SUCCESS(
            '\nListo: %d trabajadores, %d dias de tareo entre %s y %s.'
            % (len(trabajadores), dias_creados, desde, hasta)
        ))
        self.stdout.write(
            '\nLogin de prueba: usuario = DNI (ej. %s%s01), password = %s'
            % (PREFIJO_DNI, '00', PASSWORD_DEMO)
        )
        self.stdout.write(
            'Para borrar todo: manage.py seed_demo --limpiar'
        )

    # -- limpieza -------------------------------------------------------

    def _limpiar(self):
        trabajadores = Trabajador.objects.filter(dni__startswith=PREFIJO_DNI)
        total_trabajadores = trabajadores.count()
        if not total_trabajadores:
            self.stdout.write('No hay datos de prueba que borrar.')
            return

        usuarios = list(
            User.objects.filter(username__startswith=PREFIJO_DNI)
            .values_list('pk', flat=True)
        )
        tareos = TareoDiario.objects.filter(trabajador__in=trabajadores).count()
        sanciones = Sancion.objects.filter(trabajador__in=trabajadores).count()
        solicitudes = SolicitudHorasExtra.objects.filter(trabajador__in=trabajadores).count()

        # El tareo, las asignaciones, las solicitudes, las justificaciones (via
        # tareo) y las sanciones caen por CASCADE al borrar el Trabajador.
        trabajadores.delete()
        # Asistencia cuelga del Usuario (CASCADE), no del Trabajador.
        borrados_usuarios, _ = User.objects.filter(pk__in=usuarios).delete()

        self.stdout.write(self.style.SUCCESS(
            'Borrados %d trabajadores, %d dias de tareo, %d solicitudes de horas '
            'extra, %d sanciones y sus usuarios de login asociados.'
            % (total_trabajadores, tareos, solicitudes, sanciones)
        ))

    # -- catalogo ---------------------------------------------------------

    def _crear_catalogos(self):
        empresa, _ = Empresa.objects.get_or_create(
            nombre='Ceneris Testing S.A.C.',
            defaults={
                'ruc': '20700000002',
                'direccion': 'Av. Ejercito 710, Yanahuara, Arequipa',
                'telefono': '054-200200',
                'email_contacto': 'qa@ceneris-test.pe',
                'persona_contacto': 'Fabricio Salazar',
            },
        )
        sede, _ = Sede.objects.get_or_create(
            nombre='Sede QA Arequipa',
            defaults={'direccion': 'Parque Industrial Rio Seco, Cerro Colorado', 'activo': True},
        )
        centro, _ = CentroCosto.objects.get_or_create(
            codigo='QA01', defaults={'nombre': 'Centro de Costo de Pruebas'},
        )
        ubicacion, _ = Ubicacion.objects.get_or_create(
            nombre='Oficina QA Rio Seco',
            defaults={
                'hora_entrada': datetime.time(8, 0),
                'latitud': -16.3606, 'longitud': -71.5731, 'radio': 150,
            },
        )
        proyecto, _ = Proyecto.objects.get_or_create(
            nombre='Proyecto Demo QA 2026',
            defaults={
                'codigo': 'PRY-QA-01', 'empresa': empresa,
                'cliente': 'Cliente Demo', 'fecha_inicio': datetime.date(2026, 1, 2),
                'activo': True,
            },
        )

        areas = {}
        for nombre, codigo in (
            ('Operaciones', 'OPE'), ('Administracion', 'ADM'),
            ('Calidad', 'CAL'), ('Recursos Humanos', 'RRHH'),
        ):
            areas[nombre], _ = Area.objects.get_or_create(
                nombre=nombre,
                defaults={'codigo': codigo, 'descripcion': 'Area %s' % nombre},
            )

        for indice, nombre in enumerate(sorted({fila[6] for fila in PERSONAL}), start=1):
            Cargo.objects.get_or_create(
                nombre=nombre, defaults={'codigo': 'QC%03d' % indice},
            )

        self.stdout.write(
            'Catalogo listo: empresa, sede, 4 areas, centro de costo, ubicacion, '
            'proyecto y cargos.'
        )
        return {
            'empresa': empresa, 'sede': sede, 'centro': centro,
            'ubicacion': ubicacion, 'proyecto': proyecto, 'areas': areas,
        }

    def _crear_trabajadores(self, catalogos):
        hoy = timezone.localdate()
        creados = []

        for indice, fila in enumerate(PERSONAL):
            (sufijo, paterno, materno, nombres, sexo, area, cargo,
             perfil, es_jefe, es_gerente, incidencia) = fila
            dni = PREFIJO_DNI + '00' + sufijo
            email = '%s.%s@ceneris-test.pe' % (nombres.split()[0].lower(), paterno.lower())

            user, user_nuevo = User.objects.get_or_create(
                username=dni,
                defaults={
                    'first_name': nombres.split()[0],
                    'last_name': paterno,
                    'email': email,
                    'is_staff': es_gerente,
                },
            )
            if user_nuevo:
                user.set_password(PASSWORD_DEMO)
                user.save()

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
                    'user': user,
                    'fecha_ingreso': hoy - datetime.timedelta(days=365 + indice * 30),
                    'fecha_nacimiento': datetime.date(1980 + indice, (indice % 12) + 1, (indice % 27) + 1),
                    'sexo': sexo,
                    'email': email,
                    'telefono': '9%08d' % (60000000 + indice),
                    'es_jefe': es_jefe,
                    'es_gerente': es_gerente,
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
            if es_jefe:
                trabajador.areas_supervisadas.add(catalogos['areas'][area])

            creados.append((trabajador, perfil, incidencia))
            self.stdout.write('  %s %s %s, %s (%s / %s)' % (
                '+' if nuevo else '=', dni, paterno, nombres, area, cargo,
            ))

        return creados

    # -- tareo + asistencia -------------------------------------------------

    def _crear_tareos_y_asistencias(self, trabajadores, desde, hasta):
        lista_trabajadores = [t for t, _, _ in trabajadores]

        TareoDiario.objects.filter(
            trabajador__in=lista_trabajadores, fecha__gte=desde, fecha__lte=hasta,
        ).delete()
        Asistencia.objects.filter(
            usuario__in=[t.user for t in lista_trabajadores if t.user_id],
            timestamp__date__gte=desde, timestamp__date__lte=hasta,
        ).delete()

        dias_habiles = [
            desde + datetime.timedelta(days=n)
            for n in range((hasta - desde).days + 1)
            if (desde + datetime.timedelta(days=n)).weekday() < 5
        ]
        if not dias_habiles:
            raise CommandError('El rango no tiene ningun dia habil.')

        dia_incidencia = dias_habiles[len(dias_habiles) // 2]

        total_dias = 0
        for trabajador, nombre_perfil, incidencia in trabajadores:
            perfil = PERFILES[nombre_perfil]
            fecha = desde
            while fecha <= hasta:
                tareo = self._tareo_del_dia(trabajador, fecha, perfil, incidencia, dia_incidencia)
                tareo.save()
                total_dias += 1
                self._crear_marcas_del_dia(trabajador, tareo)
                fecha += datetime.timedelta(days=1)

        return total_dias

    def _tareo_del_dia(self, trabajador, fecha, perfil, incidencia, dia_incidencia):
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

    def _crear_marcas_del_dia(self, trabajador, tareo):
        """Genera las marcaciones reales (Asistencia) que respaldan el tareo,
        para que el registro en tiempo real y el mapa de asistencias tengan
        datos coherentes con lo que muestra el reporte."""
        if not trabajador.user_id or tareo.resultado != 'A':
            return

        tz = timezone.get_current_timezone()
        marcas = []
        if tareo.hora_entrada_real:
            marcas.append(('Entrada', tareo.hora_entrada_real))
        if tareo.hora_salida_real:
            marcas.append(('Salida', tareo.hora_salida_real))

        ubicacion = trabajador.ubicaciones_permitidas.first()
        for tipo, hora in marcas:
            momento = timezone.make_aware(
                datetime.datetime.combine(tareo.fecha, hora), tz,
            )
            Asistencia.objects.create(
                usuario=trabajador.user,
                timestamp=momento,
                tipo_marcacion=tipo,
                latitud=ubicacion.latitud if ubicacion else None,
                longitud=ubicacion.longitud if ubicacion else None,
                nombre_ubicacion=ubicacion.nombre if ubicacion else None,
                device_id='seed-demo-device',
                origen='APP',
                client_uuid=uuid.uuid4(),
            )

    def _sumar_minutos(self, hora, minutos):
        base = datetime.datetime.combine(datetime.date(2000, 1, 1), hora)
        return (base + datetime.timedelta(minutes=minutos)).time()

    # -- justificacion, horas extra, sanciones -------------------------------

    def _crear_justificacion(self, trabajadores):
        trabajador_falta = next(
            (t for t, _, incidencia in trabajadores if incidencia == 'falta'), None,
        )
        if not trabajador_falta:
            return
        tareo_falta = trabajador_falta.dias_tareo.filter(resultado='F').order_by('-fecha').first()
        if not tareo_falta:
            return
        Justificacion.objects.get_or_create(
            tareo=tareo_falta,
            defaults={
                'motivo': 'SALUD',
                'descripcion': 'Descanso medico por indisposicion (dato de prueba).',
                'estado_solicitud': 'PENDIENTE',
            },
        )
        self.stdout.write('Justificacion de prueba creada para %s (%s).' % (trabajador_falta, tareo_falta.fecha))

    def _crear_solicitudes_horas_extra(self, trabajadores):
        candidatos = [t for t, _, _ in trabajadores if not t.es_gerente]
        hoy = timezone.localdate()
        estados = [
            (SolicitudHorasExtra.Estado.PENDIENTE_OPERADOR, 'Cierre de campana urgente.'),
            (SolicitudHorasExtra.Estado.PENDIENTE_ADMIN, 'Apoyo en inventario mensual.'),
            (SolicitudHorasExtra.Estado.APROBADO, 'Cobertura de turno por ausencia.'),
            (SolicitudHorasExtra.Estado.RECHAZADO, 'Solicitud fuera de plazo.'),
        ]
        creadas = 0
        for (trabajador, _, _), (estado, motivo) in zip(candidatos, estados):
            _, nueva = SolicitudHorasExtra.objects.get_or_create(
                trabajador=trabajador,
                fecha_horas_extra=hoy - datetime.timedelta(days=3),
                defaults={
                    'cantidad_horas': Decimal('2.50'),
                    'justificacion': motivo,
                    'estado': estado,
                },
            )
            creadas += int(nueva)
        self.stdout.write('%d solicitudes de horas extra de prueba listas.' % creadas)

    def _crear_sanciones(self, trabajadores):
        candidatos = [t for t, _, _ in trabajadores if not t.es_gerente and not t.es_jefe]
        hoy = timezone.localdate()
        datos = [
            (Sancion.Tipo.VERBAL, 'Tardanza reiterada en el ultimo mes (dato de prueba).'),
            (Sancion.Tipo.ESCRITA, 'Incumplimiento de protocolo de seguridad (dato de prueba).'),
        ]
        creadas = 0
        for (trabajador, _, _), (tipo, contexto) in zip(candidatos, datos):
            _, nueva = Sancion.objects.get_or_create(
                trabajador=trabajador, tipo=tipo, fecha_sancion=hoy - datetime.timedelta(days=5),
                defaults={'contexto': contexto},
            )
            creadas += int(nueva)
        self.stdout.write('%d sanciones de prueba listas.' % creadas)
