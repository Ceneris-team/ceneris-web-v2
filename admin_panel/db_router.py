# admin_panel/db_router.py

class DatabaseRouter:
    """
    Un router para controlar todas las operaciones de base de datos.
    - Las apps de Django ('auth', 'contenttypes', etc.) y la app 'calidad' 
      residen en la base de datos 'default' (PostgreSQL).
    - La app 'dashboard' (Firestore) no es gestionada por el ORM de Django
      y sus modelos no deben interactuar con la BD relacional.
    """
    
    # Lista de aplicaciones que DEBEN usar la base de datos relacional
    # AÑADIMOS 'administracion' porque sus modelos (Requerimiento, RegistroConsumo, etc.)
    # viven en la base de datos relacional y deben poder relacionarse con otras apps.
    relational_apps = {
        'auth', 'contenttypes', 'sessions', 'admin',
        'calidad', 'recursoshumanos', 'cotizaciones', 'administracion', 'cenerisapp',
        'metricas_ceneris', 'accesos',
        'authtoken',  # <--- Agregado para permitir tablas de tokens
        'proyectos',
        'inventario',
        'personal',
        'notificaciones',
    }

    def db_for_read(self, model, **hints):
        """
        Dirige las lecturas de los modelos de `relational_apps` a la BD 'default'.
        """
        if model._meta.app_label in self.relational_apps:
            return 'default'
        return None # No especificar una BD para los demás (ej. dashboard)

    def db_for_write(self, model, **hints):
        """
        Dirige las escrituras de los modelos de `relational_apps` a la BD 'default'.
        """
        if model._meta.app_label in self.relational_apps:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relaciones SOLO si ambos modelos pertenecen al grupo de apps relacionales.
        Esto previene relaciones accidentales entre modelos de PostgreSQL y modelos "fantasma" de Firestore.
        """
        if (
            obj1._meta.app_label in self.relational_apps and
            obj2._meta.app_label in self.relational_apps
        ):
           return True
        # Si una de las apps no está en la lista, no se permite la relación.
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Permite las migraciones en la BD 'default' SOLO para las apps en nuestra lista.
        Esto asegura que ni `dashboard` ni ninguna otra app no relacional
        intente crear tablas.
        """
        if app_label in self.relational_apps:
            return db == 'default'
        
        # Si la app no está en la lista (ej. 'dashboard'), no permitir la migración
        # en NINGUNA base de datos gestionada por Django.
        return False