# recursoshumanos/management/commands/reset_migrations_render.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = 'Resetea las migraciones para resolver problemas de dependencias en Render'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Iniciando reset de migraciones para Render...')
        
        try:
            # Verificar si estamos en producción (si existe DATABASE_URL)
            import os
            if not os.environ.get('DATABASE_URL'):
                self.stdout.write(self.style.WARNING('⚠️  Este comando está diseñado para Render (producción).'))
                return
            
            with connection.cursor() as cursor:
                # Limpiar registros de migraciones problemáticas
                self.stdout.write('🗑️  Limpiando registros de migraciones...')
                cursor.execute("DELETE FROM django_migrations WHERE app = 'calidad'")
                cursor.execute("DELETE FROM django_migrations WHERE app = 'recursoshumanos'")
                
            # Aplicar migraciones en orden correcto
            self.stdout.write('📦 Aplicando migraciones en orden correcto...')
            call_command('migrate', 'recursoshumanos', '0001', '--fake')
            call_command('migrate', 'calidad', '0001', '--fake')
            call_command('migrate')
            
            self.stdout.write(self.style.SUCCESS('✅ Reset de migraciones completado exitosamente!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante el reset: {str(e)}'))
            raise