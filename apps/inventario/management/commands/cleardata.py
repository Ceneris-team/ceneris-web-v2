# en proyectos/management/commands/cleardata.py

from django.core.management.base import BaseCommand
from django.db import transaction

# Importa TODOS los modelos de negocio que quieres borrar
from proyectos.models import Proyecto, TareaP, SubTarea, RegistroActividad
from inventario.models import Insumo, ItemInsumo, Accesorio, RegistroReparacion, AsignacionInsumo
from personal.models import Personal, AreaTrabajo

class Command(BaseCommand):
    help = 'Elimina todos los datos de las aplicaciones de negocio, pero CONSERVA los usuarios y el admin de Django.'

    @transaction.atomic # Asegura que si algo falla, toda la operación se deshaga
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando la eliminación de todos los datos de negocio...'))

        # --- Lista de modelos a borrar en orden de dependencia inversa ---
        # Borramos primero los modelos que dependen de otros para evitar errores de ForeignKey.
        MODELS_TO_DELETE = [
            RegistroActividad,
            AsignacionInsumo,
            SubTarea,
            TareaP,
            Proyecto,
            Accesorio,
            RegistroReparacion,
            ItemInsumo,
            Insumo,
            Personal,
            AreaTrabajo,
        ]

        for model in MODELS_TO_DELETE:
            model_name = model.__name__
            self.stdout.write(f'Eliminando todos los objetos de {model_name}...')
            # ._base_manager.all().delete() es una forma de asegurar que borra todo
            # incluso si tienes managers personalizados.
            count, _ = model._base_manager.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Se eliminaron {count} objetos de {model_name}.'))

        self.stdout.write(self.style.SUCCESS('\n¡Todos los datos de negocio han sido eliminados! Los usuarios se han conservado.'))