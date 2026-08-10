from django.db import models
from django.utils import timezone
from django.db.models import Min, Max
from personal.models import Personal
from django.db.models import Sum, F
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Proyecto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    completada = models.BooleanField(default=False)
    @property
    def fecha_inicio_calculada(self):
        """
        Devuelve la fecha de inicio más temprana de TODAS las subtareas del proyecto.
        """
        # Necesitamos importar SubTarea aquí para evitar importaciones circulares
        from inventario.models import SubTarea 
        
        # Usamos aggregate para pedirle a la DB que encuentre el valor Mínimo
        resultado = SubTarea.objects.filter(tarea__proyecto=self).aggregate(Min('fecha_inicio'))
        return resultado['fecha_inicio__min'] # Devuelve la fecha o None si no hay subtareas

    @property
    def fecha_fin_calculada(self):
        """
        Devuelve la fecha de fin más tardía de TODAS las subtareas del proyecto.
        """
        from inventario.models import SubTarea
        
        resultado = SubTarea.objects.filter(tarea__proyecto=self).aggregate(Max('fecha_fin'))
        return resultado['fecha_fin__max']

    def __str__(self):
        return self.nombre

class TareaP(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='tareas')
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    @property
    def fecha_inicio_calculada(self):
        """Devuelve la fecha de inicio más temprana de todas sus subtareas."""
        # Usamos 'aggregate' para pedirle a la DB que encuentre el valor Mínimo
        resultado = self.subtareas.aggregate(Min('fecha_inicio'))
        return resultado['fecha_inicio__min']

    @property
    def fecha_fin_calculada(self):
        """Devuelve la fecha de fin más tardía de todas sus subtareas."""
        # Usamos 'aggregate' para pedirle a la DB que encuentre el valor Máximo
        resultado = self.subtareas.aggregate(Max('fecha_fin'))
        return resultado['fecha_fin__max']

    @property
    def costo_total_insumos(self):
        """Suma los costos de todas sus subtareas."""
        total = 0
        # Iteramos sobre sus subtareas y sumamos el costo de cada una
        for subtarea in self.subtareas.all():
            total += subtarea.costo_total_insumos
        return total

    completada = models.BooleanField(default=False)

    def __str__(self):
        return self.titulo

class SubTarea(models.Model):
    tarea = models.ForeignKey(TareaP, on_delete=models.CASCADE, related_name='subtareas')
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)
    completada = models.BooleanField(default=False)
    def dia_semana(self):
        """Devuelve el nombre del día de la semana en español."""
        # weekday() devuelve 0 para Lunes, 1 para Martes, etc.
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        return dias[self.fecha_inicio.weekday()]
    
    personal_asignado = models.ManyToManyField(
        Personal,
        related_name='subtareas_asignadas',
        blank=True  
    )

    @property
    def costo_total_insumos(self):
        """Suma los costos de todos los insumos asignados a esta subtarea."""
        # La base de datos multiplica la cantidad por el costo registrado de cada asignación
        # y luego suma todos los resultados. Es muy eficiente.
        total = self.insumos_asignados.aggregate(
            costo_calculado=Sum(F('cantidad_asignada') * F('costo_unitario_registrado'))
        )['costo_calculado']
        # Si no hay insumos, el resultado es None. Lo convertimos a 0.00.
        return total or 0.00

    def __str__(self):
        return self.titulo

class RegistroActividad(models.Model):
    ACCIONES = (
        ('CREACION', 'Creación'),
        ('ACTUALIZACION', 'Actualización'),
        ('ELIMINACION', 'Eliminación'),
        ('LOGIN', 'Inicio de Sesión'),
    )

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=20, choices=ACCIONES)
    timestamp = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, null=True)

    # --- Campos Genéricos para apuntar a CUALQUIER objeto ---
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.usuario} - {self.accion} en {self.content_object} a las {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']