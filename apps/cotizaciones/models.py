from django.db import models
from django.db.models import Sum, F
from decimal import Decimal
from django.contrib.auth.models import User # Para registrar quién hace la acción
from simple_history.models import HistoricalRecords # <-- IMPORTAR ESTO

# Create your models here.


class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=200)
    ruc = models.CharField(max_length=13, unique=True)

    def __str__(self):
        return self.nombre

class Contacto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre

class ProcesoCotizacion(models.Model):
    """
    Este modelo centraliza todo el flujo, desde la primera cita
    hasta que se genera la cotización final.
    """
    # Información básica
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    contacto = models.ForeignKey(Contacto, on_delete=models.CASCADE)

    # Etapa 1: Agendar Cita
    fecha_citacion = models.DateTimeField(verbose_name="Fecha de Citación")
    usuario_agenda = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="citas_agendadas", verbose_name="Usuario que agenda")

    # Etapa 2: Encuentro con Cliente
    fecha_encuentro = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Encuentro con Cliente")
    usuario_encuentro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="encuentros_realizados", verbose_name="Usuario en Encuentro")

    # Etapa 3: Cotización (el enlace al modelo final)
    cotizacion_final = models.OneToOneField('Cotizaciones', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cotización Final")

    # Campos de seguimiento
    creado_el = models.DateTimeField(auto_now_add=True)
    modificado_el = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Proceso para {self.empresa.nombre}"

    def get_estado_proceso_display(self):
        """Devuelve una descripción clara del estado actual del proceso."""
        if self.cotizacion_final:
            # Si hay una cotización, usamos su estado.
            # get_estado_display es un método que Django crea automáticamente para los campos con 'choices'.
            return self.cotizacion_final.get_estado_display()
        elif self.fecha_encuentro:
            return "Listo para Cotizar"
        else:
            return "Pendiente de Encuentro"

    def get_estado_badge_class(self):
        """Devuelve una clase de CSS de Bootstrap para el color del badge."""
        if self.cotizacion_final:
            estado = self.cotizacion_final.estado
            if estado == 'aprobada': return 'bg-success'
            if estado == 'rechazada': return 'bg-danger'
            if estado == 'enviada': return 'bg-primary'
            if estado == 'borrador': return 'bg-warning text-dark' # ¡Importante para destacar borradores!
        elif self.fecha_encuentro:
            return 'bg-info'
        return 'bg-secondary'

class Cotizaciones(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]
    # Se eliminan 'empresa' y 'contacto' para evitar redundancia.
    descripcion_pedido = models.TextField()
    tipo_servicio_producto = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')

    # Campos para totales (calculados)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="IGV (18%)")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    usuario_creador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="cotizaciones_creadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    def __str__(self):
        try:
            return f"Cotización #{self.id} para {self.procesocotizacion.empresa.nombre}"
        except:
            return f"Cotización #{self.id}"

    def calcular_totales(self):
        """Calcula los totales basados en los detalles y actualiza el modelo."""
        # Usamos el ORM para sumar los subtotales de los detalles relacionados
        data = self.detalles.aggregate(
            subtotal_calculado=Sum(F('cantidad') * F('precio_unitario'))
        )
        # Aseguramos trabajar con Decimal para evitar operaciones Decimal * float
        subtotal_calc = data.get('subtotal_calculado') or Decimal('0.00')
        # subtotal_calc normalmente será Decimal (porque precio_unitario es DecimalField)
        self.subtotal = subtotal_calc
        self.igv = (self.subtotal * Decimal('0.18')).quantize(Decimal('0.01'))
        self.total = (self.subtotal + self.igv).quantize(Decimal('0.01'))
        self.save()


class LogAcciones(models.Model):
    cotizacion = models.ForeignKey(Cotizaciones, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL,null=True)
    accion = models.CharField(max_length=200)
    fecha = models.DateTimeField(auto_now_add=True)

class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizaciones, related_name='detalles', on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=255, verbose_name="Descripción del Ítem")
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    
    # Este campo no es necesario, lo calcularemos dinámicamente
    # subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.cantidad} x {self.descripcion}"

