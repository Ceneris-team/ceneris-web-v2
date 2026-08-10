# recursoshumanos/management/commands/create_superuser_from_env.py

import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea un superusuario de forma no interactiva usando variables de entorno.'

    def handle(self, *args, **options):
        # Lee los datos desde las variables de entorno
        username = os.environ.get('ADMIN_USER')
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')

        # Valida que todas las variables necesarias estén presentes
        if not all([username, email, password]):
            raise CommandError('Faltan las variables de entorno ADMIN_USER, ADMIN_EMAIL o ADMIN_PASSWORD.')

        # Comprueba si el usuario ya existe
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'El superusuario "{username}" ya existe. No se hace nada.'))
            return

        # Crea el superusuario
        self.stdout.write(f'Creando superusuario "{username}"...')
        User.objects.create_superuser(username=username, email=email, password=password)
        
        self.stdout.write(self.style.SUCCESS(f'Superusuario "{username}" creado exitosamente.'))