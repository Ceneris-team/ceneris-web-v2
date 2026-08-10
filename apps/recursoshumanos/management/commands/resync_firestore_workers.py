# recursoshumanos/management/commands/resync_firestore_workers.py

import os
from django.core.management.base import BaseCommand
from recursoshumanos.models import Trabajador
import firebase_admin
from firebase_admin import credentials, firestore

class Command(BaseCommand):
    help = 'Borra y re-sincroniza todos los trabajadores de Django a Firestore, usando el PK como ID del documento.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- INICIANDO RE-SINCRONIZACIÓN DE TRABAJADORES A FIRESTORE ---'))

        # --- Conexión a Firestore ---
        try:
            if not firebase_admin._apps:
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
        
        # --- Lógica de Sincronización ---
        trabajadores = Trabajador.objects.all()
        total = trabajadores.count()
        creados_count = 0
        errores_count = 0

        self.stdout.write(f'Se encontraron {total} trabajadores en Django para sincronizar.')
        
        # Obtenemos la referencia a la colección
        collection_ref = db.collection('trabajadores')

        for i, trabajador in enumerate(trabajadores):
            pk_str = str(trabajador.pk)
            self.stdout.write(f'({i+1}/{total}) Procesando trabajador PK: {pk_str}...', ending='')

            try:
                # Construimos el diccionario de datos exactamente como en tu estructura de Firestore
                data_to_set = {
                    'activo': trabajador.activo,
                    'cargo': trabajador.cargo.nombre if trabajador.cargo else '',
                    'deviceIdVinculado': None,  # Se inicializa como nulo, ya que este dato vive solo en Firestore
                    'email': trabajador.email or '',
                    'nombre': str(trabajador), # Asume que el método __str__ del modelo devuelve el nombre completo
                    'sexo': trabajador.get_sexo_display() or '',
                    'dni': trabajador.dni,
                }
                
                # Usamos set() para crear el documento con el ID específico (el PK)
                collection_ref.document(pk_str).set(data_to_set)

                self.stdout.write(self.style.SUCCESS(' ¡CREADO!'))
                creados_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f' ¡ERROR! -> {e}'))
                errores_count += 1

        self.stdout.write(self.style.SUCCESS('--- SINCRONIZACIÓN COMPLETADA ---'))
        self.stdout.write(f'Resultados: {creados_count} documentos creados, {errores_count} errores.')