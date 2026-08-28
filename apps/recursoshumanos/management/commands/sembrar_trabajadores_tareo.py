"""
Da de alta trabajadores de PRUEBA con los nombres que trae el Excel de tareo
del proyecto, para poder probar la importación de punta a punta.

El Excel no trae DNI, así que los DNI son ficticios (79000001 en adelante) y
los apellidos maternos salen de la hoja auxiliar del archivo cuando existen.
NO son datos reales: bórralos antes de pasar a producción con

    python manage.py sembrar_trabajadores_tareo --borrar
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from recursoshumanos.models import Area, Trabajador

# Rango reservado para estas altas de prueba. Se usa también para borrarlas.
DNI_BASE = 79000000

# (nombres, apellido_paterno, apellido_materno)
# Los apellidos maternos marcados vienen de la hoja auxiliar del propio Excel;
# el resto es relleno, porque el modelo exige el campo.
PERSONAL = [
    ('SHAMIR OSNAR', 'ACHO', 'MEDINA'),            # hoja auxiliar
    ('SONNY', 'ALVIRI', 'DEL CARPIO'),
    ('CHRISTOPHER', 'BEGAZO', 'RIVERA'),
    ('ALIOSKA', 'CARDENAS', 'TORRES'),
    ('GLEYSER', 'CARNERO', 'FLORES'),
    ('DANNY MARIO', 'CCAMA', 'CCORA'),             # hoja auxiliar
    ('HENRY GONZALO', 'CCAMA', 'LLANQUE'),         # hoja auxiliar
    ('HENRRY ALDAIR', 'CERPA', 'LINARES'),         # hoja auxiliar
    ('RONALD', 'CORNEJO', 'VARGAS'),
    ('DIEGO', 'HERNANI', 'PAREDES'),
    ('JULIO', 'HUAMAN', 'CONDORI'),
    ('KLEIDER', 'JAITA', 'MAMANI'),
    ('MARIA', 'LAROTA', 'CHOQUE'),
    ('ELIAN', 'MENDOZA', 'ROJAS'),
    ('FIORELLA XIMENA', 'MIRANDA', 'SALAS'),       # hoja auxiliar
    ('YERSON', 'MOLLO', 'APAZA'),
    ('DANERY', 'NIETO', 'SALAS'),
    ('DANIEL ALONSO', 'OTAZU', 'ZEA'),             # hoja auxiliar
    ('WASHINGTON', 'PALOMINO', 'CHAVEZ'),
    ('EDWIN', 'PUMA', 'QUISPE'),
    ('EDU MIGUEL', 'QUINTANILLA', 'MASIAS'),       # hoja auxiliar
    ('VICTOR', 'QUIÑONES', 'MACHACCA'),            # hoja auxiliar
    ('CARLOS', 'ROJAS', 'MEZA'),
    ('JEANCARLO', 'SALDIVAR', 'PINTO'),
    ('ALEXANDER', 'SANCHEZ', 'DELGADO'),
    ('JEYSSON RAUL', 'SOLIS', 'VELASQUEZ'),        # hoja auxiliar
    ('DIEGO', 'ZEGARRA', 'NUÑEZ'),
    ('JESUS', 'ZUÑIGA', 'ARANIBAR'),
    ('BRYAN', 'ESPEDILLA', 'CACERES'),
    # Altas de agosto. Van al final a propósito: el DNI sale del índice en esta
    # lista, así que insertarlas en medio renombraría a las de arriba.
    ('JESUS', 'ADRIAZOLA', 'HUAMANI'),
    ('ALFONSO', 'ARANIBAR', 'PACHECO'),
    ('BRIAN', 'RAMOS', 'QUISPE'),
    ('ANDRES', 'CABALLERO', 'VILCA'),
    ('JUAN', 'CCALAHUILLE', 'MAMANI'),
    ('KEVIN', 'CCORAHUA', 'FLORES'),
]


class Command(BaseCommand):
    help = ("Crea (o borra) trabajadores de prueba con los nombres del Excel "
            "de tareo del proyecto.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--borrar', action='store_true',
            help='Elimina los trabajadores de prueba creados por este comando.')
        parser.add_argument(
            '--area', type=int, default=None,
            help='ID del área a asignar (por defecto, la que se llame "Operaciones QA").')

    def handle(self, *args, **opciones):
        if opciones['borrar']:
            return self._borrar()
        return self._crear(opciones['area'])

    def _dni(self, indice):
        return str(DNI_BASE + indice + 1)

    def _borrar(self):
        dnis = [self._dni(i) for i in range(len(PERSONAL))]
        borrados, _ = Trabajador.objects.filter(dni__in=dnis).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Eliminados {borrados} registro(s) de prueba."))

    def _crear(self, area_id):
        if area_id is not None:
            area = Area.objects.filter(id=area_id).first()
        else:
            area = Area.objects.filter(nombre__icontains='Operaciones QA').first()
        if area is None:
            area = Area.objects.order_by('id').first()

        creados = existentes = 0
        with transaction.atomic():
            for indice, (nombres, paterno, materno) in enumerate(PERSONAL):
                _, nuevo = Trabajador.objects.get_or_create(
                    dni=self._dni(indice),
                    defaults={
                        'nombres': nombres,
                        'apellido_paterno': paterno,
                        'apellido_materno': materno,
                        'area': area,
                        'activo': True,
                    },
                )
                if nuevo:
                    creados += 1
                else:
                    existentes += 1

        self.stdout.write(self.style.SUCCESS(
            f"Creados {creados} trabajador(es) de prueba"
            + (f", {existentes} ya existían" if existentes else "")
            + f". Área asignada: {area.nombre if area else 'ninguna'}."))
        self.stdout.write(
            "DNI ficticios del "
            f"{self._dni(0)} al {self._dni(len(PERSONAL) - 1)}. "
            "Para revertir: python manage.py sembrar_trabajadores_tareo --borrar")
