# recursoshumanos/management/commands/migrar_trabajadores.py
from django.core.management.base import BaseCommand
from recursoshumanos.models import Trabajador, Empresa # Importamos los modelos necesarios
from admin_panel.settings import db

class Command(BaseCommand):
    help = 'Migra los trabajadores desde una estructura simple de Firestore a PostgreSQL.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Iniciando migración de trabajadores desde Firestore ---'))
        
        # --- PASO 1: Obtener una empresa por defecto de PostgreSQL ---
        try:
            # CAMBIA '1' por el ID de la empresa principal que creaste en el admin de Django
            empresa_por_defecto = Empresa.objects.get(pk=1) 
            self.stdout.write(f"Todos los trabajadores se asignarán a la empresa por defecto: '{empresa_por_defecto.nombre}'")
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR('¡ERROR CRÍTICO! No se encontró una empresa por defecto (ID=1).'))
            self.stdout.write(self.style.WARNING('Por favor, crea al menos una empresa en el panel de admin de Django antes de ejecutar este script.'))
            return

        # --- PASO 2: Leer los documentos de Firestore ---
        try:
            firestore_trabajadores = list(db.collection('trabajadores').stream())
            self.stdout.write(f"Se encontraron {len(firestore_trabajadores)} documentos de trabajadores en Firestore.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al conectar o leer de Firestore: {e}"))
            return

        # --- PASO 3: Procesar y guardar cada trabajador ---
        migrados_count = 0
        errores_count = 0
        for doc in firestore_trabajadores:
            data = doc.to_dict()
            dni = doc.id

            # Validación del DNI
            if not dni or not dni.isdigit() or len(dni) < 7:
                self.stdout.write(self.style.WARNING(f"  [OMITIDO] Documento con ID/DNI inválido: '{dni}'"))
                continue

            # Comprobar si ya existe en PostgreSQL
            if Trabajador.objects.filter(dni=dni).exists():
                continue

            try:
                # --- LÓGICA DE EXTRACCIÓN ADAPTADA ---
                # Leemos los campos que SÍ existen en Firestore
                nombre_completo = data.get('nombre', '').strip()
                activo = data.get('activo', True) # Tomamos el valor de 'activo'

                # Lógica para separar apellidos y nombres (ajusta si el formato es diferente)
                # Formato esperado: "APELLIDO_P APELLIDO_M, NOMBRES"
                partes_coma = nombre_completo.split(',')
                apellidos = partes_coma[0].strip()
                nombres = partes_coma[1].strip() if len(partes_coma) > 1 else ''
                
                partes_apellidos = apellidos.split()
                apellido_paterno = partes_apellidos[0] if len(partes_apellidos) > 0 else apellidos
                apellido_materno = " ".join(partes_apellidos[1:]) if len(partes_apellidos) > 1 else ''

                # --- CREACIÓN DEL OBJETO EN POSTGRESQL ---
                Trabajador.objects.create(
                    dni=dni,
                    nombres=nombres,
                    apellido_paterno=apellido_paterno,
                    apellido_materno=apellido_materno,
                    activo=activo,
                    empresa=empresa_por_defecto, # ¡Campo obligatorio con valor por defecto!
                    # Los demás campos (proyecto, fechas, etc.) se quedarán con sus
                    # valores por defecto (NULL o vacíos) definidos en el modelo.
                )
                
                migrados_count += 1
                self.stdout.write(f"  [OK] Migrado DNI: {dni}")

            except Exception as e:
                errores_count += 1
                self.stdout.write(self.style.ERROR(f"  [ERROR] Al migrar DNI {dni}: {e}"))
        
        self.stdout.write(self.style.SUCCESS('--- Migración completada ---'))
        self.stdout.write(f"Trabajadores migrados exitosamente: {migrados_count}")
        self.stdout.write(f"Errores encontrados: {errores_count}")