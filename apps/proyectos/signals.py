# en proyectos/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
# Necesitamos una forma de pasar el 'request' a las señales. Usaremos un middleware.
from .middleware import get_current_user

from .models import Proyecto, TareaP, SubTarea, RegistroActividad
from inventario.models import Insumo, ItemInsumo
from personal.models import Personal

# --- FUNCIÓN DE UTILIDAD PARA REGISTRAR LA ACTIVIDAD ---
def registrar_actividad(instancia, accion, descripcion=""):
    usuario = get_current_user()
    if not hasattr(instancia, 'pk') or not instancia.pk:
        return

    RegistroActividad.objects.create(
        usuario=usuario,
        accion=accion,
        content_type=ContentType.objects.get_for_model(instancia),
        object_id=instancia.pk,
        descripcion=descripcion
    )

# --- DICCIONARIO GLOBAL PARA GUARDAR EL ESTADO "ANTES" ---
# Usaremos esto para almacenar temporalmente el estado de un objeto antes de que se guarde
before_save_instance = {}

# --- SEÑALES PARA TODOS TUS MODELOS ---
MODELS_TO_TRACK = [Proyecto, TareaP, SubTarea, Insumo, ItemInsumo, Personal]

# 1. ANTES DE GUARDAR (pre_save): Guardamos una copia del estado original
@receiver(pre_save)
def store_before_save(sender, instance, **kwargs):
    if sender in MODELS_TO_TRACK and instance.pk:
        try:
            # Obtenemos la versión del objeto que está en la BBDD
            before_save_instance[instance.pk] = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass

# 2. DESPUÉS DE GUARDAR (post_save): Comparamos y registramos
@receiver(post_save)
def registrar_guardado(sender, instance, created, **kwargs):
    if sender not in MODELS_TO_TRACK:
        return

    if created:
        # Si es un objeto nuevo, la descripción es simple
        registrar_actividad(instance, 'CREACION', f'Se creó el objeto: {instance}')
    else:
        # Si es una actualización, comparamos campos
        if instance.pk in before_save_instance:
            old_instance = before_save_instance.pop(instance.pk)
            changes = []
            # Comparamos los campos del objeto antiguo con el nuevo
            for field in instance._meta.fields:
                if field.name in ['id', 'fecha_ingreso', 'timestamp']: continue # Ignorar campos que siempre cambian
                
                old_value = getattr(old_instance, field.name)
                new_value = getattr(instance, field.name)
                if old_value != new_value:
                    changes.append(f"'{field.verbose_name}' cambió de '{old_value}' a '{new_value}'")
            
            if changes:
                descripcion = "; ".join(changes)
                registrar_actividad(instance, 'ACTUALIZACION', descripcion)

# 3. DESPUÉS DE ELIMINAR (post_delete)
@receiver(post_delete)
def registrar_eliminacion(sender, instance, **kwargs):
    if sender in MODELS_TO_TRACK:
        descripcion = f'Se eliminó el objeto: {str(instance)} (ID: {instance.pk})'
        registrar_actividad(instance, 'ELIMINACION', descripcion)