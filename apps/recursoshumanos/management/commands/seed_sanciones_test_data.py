from django.core.management.base import BaseCommand
from django.db import transaction

from recursoshumanos.models import Area, Empresa, Trabajador


class Command(BaseCommand):
    help = (
        'Crea datos de prueba (Empresa, Area y 2 Trabajadores) para probar '
        'la pantalla de Sanciones en local. Es idempotente: si ya existen '
        'los registros de prueba, los reutiliza en vez de duplicarlos.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        empresa, creada_empresa = Empresa.objects.get_or_create(
            nombre='Empresa de Prueba SAC',
            defaults={
                'ruc': '20999999999',
                'direccion': 'Av. de Prueba 123, Lima',
                'telefono': '999999999',
                'email_contacto': 'pruebas@ceneris-test.com',
                'persona_contacto': 'Contacto de Prueba',
            },
        )
        self._log(creada_empresa, 'Empresa', empresa.nombre)

        area, creada_area = Area.objects.get_or_create(
            nombre='Área de Prueba',
            defaults={
                'codigo': 'PRB-01',
                'descripcion': 'Área creada para probar el módulo de Sanciones.',
            },
        )
        self._log(creada_area, 'Área', area.nombre)

        trabajadores_data = [
            {
                'dni': '87654321',
                'apellido_paterno': 'Pérez',
                'apellido_materno': 'Gómez',
                'nombres': 'Juan Carlos',
                'cargo': 'Operario de Prueba',
                'email': 'juan.perez.prueba@ceneris-test.com',
                'telefono': '987654321',
                'sexo': 'M',
            },
            {
                'dni': '12345678',
                'apellido_paterno': 'Ramírez',
                'apellido_materno': 'Soto',
                'nombres': 'María Fernanda',
                'cargo': 'Asistente de Prueba',
                'email': 'maria.ramirez.prueba@ceneris-test.com',
                'telefono': '912345678',
                'sexo': 'F',
            },
        ]

        for datos in trabajadores_data:
            dni = datos.pop('dni')
            trabajador, creado = Trabajador.objects.get_or_create(
                dni=dni,
                defaults={
                    **datos,
                    'empresa': empresa,
                    'area': area,
                    'fecha_ingreso': '2024-01-01',
                    'activo': True,
                },
            )
            if not creado:
                # Asegura que quede vinculado a la empresa/área de prueba
                # aunque ya existiera de una corrida anterior.
                actualizar = False
                if trabajador.empresa_id != empresa.id:
                    trabajador.empresa = empresa
                    actualizar = True
                if trabajador.area_id != area.id:
                    trabajador.area = area
                    actualizar = True
                if actualizar:
                    trabajador.save(update_fields=['empresa', 'area'])
            self._log(creado, 'Trabajador', f'{trabajador} (DNI {trabajador.dni})')

        self.stdout.write(self.style.SUCCESS(
            '\nListo. Ve a /recursoshumanos/sanciones/ para probar el módulo '
            'con estos trabajadores de prueba.'
        ))

    def _log(self, creado, etiqueta, nombre):
        if creado:
            self.stdout.write(self.style.SUCCESS(f'[Creado] {etiqueta}: {nombre}'))
        else:
            self.stdout.write(self.style.WARNING(f'[Ya existía] {etiqueta}: {nombre}'))
