# recursoshumanos/management/commands/sync_workers_to_firestore.py

import os
from django.core.management.base import BaseCommand
from recursoshumanos.models import Trabajador # Asegúrate que la ruta a tu modelo es correcta
import firebase_admin
from firebase_admin import credentials, firestore

class Command(BaseCommand):
    help = 'Sincroniza todos los trabajadores de la base de datos PostgreSQL a Firestore.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- INICIANDO SINCRONIZACIÓN DE TRABAJADORES A FIRESTORE ---'))

        # --- 1. Conexión a Firestore ---
        # Este código asume que tienes configuradas tus credenciales de Firebase
        # a través de variables de entorno, lo cual es la práctica estándar en Render.
        try:
            if not firebase_admin._apps:
                # Si usas un archivo json local, asegúrate de que la ruta sea correcta.
                # En Render, esto usa la variable de entorno GOOGLE_APPLICATION_CREDENTIALS.
                cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if not cred_path:
                    self.stdout.write(self.style.ERROR('La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada.'))
                    return
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            
            db = firestore.client()
            self.stdout.write(self.style.SUCCESS('Conexión con Firestore establecida.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al conectar con Firestore: {e}'))
            return
        
        # --- 2. Obtener datos y sincronizar ---
        trabajadores_locales = Trabajador.objects.all()
        total = trabajadores_locales.count()
        sincronizados = 0
        errores = 0

        self.stdout.write(f'Se encontraron {total} trabajadores en PostgreSQL para sincronizar.')
        
        # Obtenemos la referencia a la colección de Firestore
        collection_ref = db.collection('trabajadores')

        for i, trabajador in enumerate(trabajadores_locales):
            pk_str = str(trabajador.pk)
            self.stdout.write(f'({i+1}/{total}) Sincronizando trabajador PK: {pk_str} ({trabajador})...', ending='')

            try:
                # --- Construimos el diccionario de datos ---
                # Esta estructura es una copia exacta de la que usas en tu vista `crear_trabajador`.
                firestore_data = {
                    'nombre': str(trabajador),
                    'cargo': trabajador.cargo.nombre if trabajador.cargo else '',
                    'activo': trabajador.activo,
                    'deviceIdVinculado': None,  # Se inicializa como nulo
                    'ubicacionesPermitidas': [], # Se inicializa como lista vacía
                    'email': trabajador.email or '',
                    'sexo': trabajador.get_sexo_display() or '',
                    'dni': trabajador.dni,
                }
                
                # Usamos .set() para crear el documento con el ID específico (el PK).
                # Si el documento ya existe, .set() lo SOBRESCRIBIRÁ.
                collection_ref.document(pk_str).set(firestore_data)

                self.stdout.write(self.style.SUCCESS(' ¡OK!'))
                sincronizados += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f' ¡ERROR! -> {e}'))
                errores += 1

        self.stdout.write(self.style.SUCCESS('--- SINCRONIZACIÓN COMPLETADA ---'))
        self.stdout.write(f'Resultados: {sincronizados} sincronizados, {errores} errores.')