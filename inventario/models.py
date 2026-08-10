from django.db import models
from django.utils import timezone
from proyectos.models import SubTarea
from datetime import timedelta, datetime

class Insumo(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50, help_text="Ej: unidades, kg, metros, horas")
    
    costo_unitario_actual = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, blank=True, null=True)

    @property
    def stock_calculado(self):
        return self.items.filter(estado='EN STOCK').count()

    def __str__(self):
        return f"{self.nombre} (${self.costo_unitario_actual}/{self.unidad_medida})"


class ItemInsumo(models.Model):
    """
    Representa un insumo específico e individual con su propio número de serie.
    """
    ESTADOS = (
        ('EN STOCK', 'En Stock'),
        ('EN REPARACION', 'En Reparación'),
        ('DAÑADO', 'Dañado'),
        ('INSTALADO', 'Instalado'),
        ('EN CALIBRACION', 'En Calibración'),
        ('PRESTADO', 'Prestado'),
    )
    
    # Relación con el tipo de insumo general
    insumo_padre = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='items')
    
    codigo_interno = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Código Interno")
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, unique=True, verbose_name="Serie del Equipo")
    
    # Campos de Calibración
    fecha_calibracion = models.DateField(null=True, blank=True, verbose_name="Última Calibración")
    fecha_prox_calibracion = models.DateField(null=True, blank=True, verbose_name="Próxima Calibración")
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN STOCK')
    fecha_ingreso = models.DateField(auto_now_add=True, null=True, blank=True)

    @property
    def necesita_calibracion_pronto(self):
        """Devuelve True si la próxima calibración es en 30 días o menos."""
        if not self.fecha_prox_calibracion:
            return False
        return self.fecha_prox_calibracion <= timezone.now().date() + timedelta(days=30)

    @property
    def calibracion_vencida(self):
        """Devuelve True si la fecha de próxima calibración ya pasó."""
        if not self.fecha_prox_calibracion:
            return False
        return self.fecha_prox_calibracion < timezone.now().date()

    def __str__(self):
        return f"{self.insumo_padre.nombre} (S/N: {self.numero_serie})"

class AsignacionInsumo(models.Model):
    
    subtarea = models.ForeignKey(SubTarea, on_delete=models.CASCADE, related_name='insumos_asignados')
    item_insumo = models.ForeignKey(ItemInsumo, on_delete=models.CASCADE) 
    costo_unitario_registrado = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def costo_total(self):
        """Calcula el costo total de esta asignación específica."""
        return self.cantidad_asignada * self.costo_unitario_registrado

    class Meta:
        unique_together = ('subtarea', 'item_insumo')

    def __str__(self):
        return f"{self.cantidad_asignada} {self.insumo.unidad_medida} de {self.insumo.nombre} para {self.subtarea.titulo}"



class RegistroReparacion(models.Model):
    fecha_reporte = models.DateField(default=timezone.now)
    descripcion = models.TextField(help_text="Describe el problema y la solución aplicada.")
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    item_insumo = models.ForeignKey(
        ItemInsumo, 
        on_delete=models.CASCADE,
        related_name='reparaciones'
    )

    class Meta:
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"Reparación para {self.item_insumo} el {self.fecha_reporte}"

class Accesorio(models.Model):
    """
    Representa un accesorio individual con su propio número de serie,
    asociado a un ItemInsumo específico.
    """
    item_insumo = models.ForeignKey(ItemInsumo, on_delete=models.CASCADE, related_name='accesorios_list')
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Accesorio", blank=True,null=True)
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name="Número de Serie del Accesorio",null=True)
    ubicacion = models.CharField(max_length=200, blank=True, verbose_name="Ubicación Actual", null=True)
    fecha_calibracion = models.DateField(null=True, blank=True, verbose_name="Última Calibración (Accesorio)")
    fecha_prox_calibracion = models.DateField(null=True, blank=True, verbose_name="Próxima Calibración (Accesorio)")

    class Meta:
        # Evita duplicados para el mismo item
        unique_together = ('item_insumo', 'nombre', 'numero_serie')
    
    @property
    def necesita_calibracion_pronto(self):
        """Devuelve True si la próxima calibración es en 30 días o menos."""
        if not self.fecha_prox_calibracion:
            return False
        return self.fecha_prox_calibracion <= timezone.now().date() + timedelta(days=30)

    @property
    def calibracion_vencida(self):
        """Devuelve True si la fecha de próxima calibración ya pasó."""
        if not self.fecha_prox_calibracion:
            return False
        return self.fecha_prox_calibracion < timezone.now().date()

    def __str__(self):
        return f"{self.nombre} (S/N: {self.numero_serie}) para {self.item_insumo.numero_serie}"