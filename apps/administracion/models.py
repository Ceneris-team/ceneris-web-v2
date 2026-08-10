# administracion/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from dateutil.relativedelta import relativedelta

class Agente(models.Model):
    nombre_agente = models.CharField(
        max_length=200, 
        unique=True, 
        help_text="Nombre único del agente o producto (Ej: Ruido, Partículas respirables y sílice)"
    )
    activo = models.BooleanField(default=True, help_text="Desmarcar para ocultar este agente de nuevos requerimientos.")
    # Precio unitario asociado al agente (para cálculos de valor total)
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Precio unitario por este agente (p. ej. 150.50)",
        validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return self.nombre_agente

    class Meta:
        # Ordenamos los agentes alfabéticamente por defecto
        ordering = ['nombre_agente']

class Requerimiento(models.Model):
    agente = models.ForeignKey(
        Agente, 
        on_delete=models.PROTECT, # PROTECT evita borrar un agente si ya está en uso en un requerimiento.
        help_text="Seleccione el agente o producto del catálogo."
    )
    TIPO_OCUPACIONAL = 'Ocupacional'
    TIPO_CONTROLADO = 'Controlado'
    TIPO_AMBIENTES = 'Ambientes de Trabajo'
    TIPO_ERGONOMIA = 'Ergonomia'
    TIPO_MONITOREO_CHOICES = [
        (TIPO_OCUPACIONAL, 'Ocupacional'),
        (TIPO_CONTROLADO, 'Controlado'),
        (TIPO_AMBIENTES, 'Ambientes de Trabajo'),
        (TIPO_ERGONOMIA, 'Ergonomía'),
    ]
    tipo_monitoreo = models.CharField(
        max_length=50, 
        choices=TIPO_MONITOREO_CHOICES,
        help_text="Seleccione el tipo de monitoreo"
    )
    # NOTE: `agente` is a ForeignKey to the Agente catalog. Do not redefine it as a CharField.
    cantidad_total = models.PositiveIntegerField(help_text="Cantidad total requerida para el período")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    meta_mensual = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agente} - {self.tipo_monitoreo} ({self.fecha_inicio.year})"

    def clean(self):
        # --- INICIO DEL CAMBIO ---
        # Solo intentamos comparar las fechas SI AMBAS EXISTEN.
        # Esto evita el error 'NoneType' < 'NoneType'.
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio.")
        # --- FIN DEL CAMBIO ---

    def save(self, *args, **kwargs):
        if self.fecha_inicio and self.fecha_fin:
            # 1. Usamos relativedelta para obtener la diferencia en años y meses enteros.
            diff = relativedelta(self.fecha_fin, self.fecha_inicio)
            meses_totales = diff.years * 12 + diff.months

            # 2. Si el período es menor a un mes, lo contamos como 1 para evitar división por cero.
            if meses_totales <= 0:
                meses_totales = 1
            
            # 3. Calculamos la meta
            if self.cantidad_total:
                # 4. Redondeamos el resultado final a 2 decimales.
                self.meta_mensual = round(self.cantidad_total / meses_totales, 2)
            else:
                self.meta_mensual = 0
        else:
            self.meta_mensual = 0
            
        super().save(*args, **kwargs)

# El modelo RegistroConsumo no necesita cambios.
class RegistroConsumo(models.Model):
    MONTH_CHOICES = [
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ]
    requerimiento = models.ForeignKey(Requerimiento, on_delete=models.CASCADE, related_name="registros")
    mes = models.PositiveIntegerField(choices=MONTH_CHOICES)
    año = models.PositiveIntegerField()
    # Permitimos valores decimales (ej. 150.50). Antes era PositiveIntegerField.
    # Usamos DecimalField por precisión y MinValueValidator para evitar negativos.
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Registro para {self.requerimiento.agente} - {self.mes}/{self.año}"

