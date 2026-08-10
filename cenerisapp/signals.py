from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Dispositivo, Calibracion, Parte
from django.contrib.auth.models import Group, User
from .models import Empleado

@receiver(post_save, sender=Dispositivo)
def crear_registro_calibracion_inicial(sender, instance, created, **kwargs):
    
    if created:
        
        Calibracion.objects.create(id_dispositivo=instance)
        print(f"Registro de calibración inicial creado para el dispositivo: {instance}")

@receiver(post_save, sender=Empleado)
def asignar_grupo_por_puesto(sender, instance, created, **kwargs):
    
    if instance.user:
        try:
            puesto = instance.puesto.strip().capitalize()
            
            grupo = Group.objects.get(name=puesto)
            
            instance.user.groups.clear()
            
            instance.user.groups.add(grupo)
            
        except Group.DoesNotExist:
            instance.user.groups.clear()
            print(f"Advertencia: No se encontró un grupo para el puesto '{instance.puesto}'.")