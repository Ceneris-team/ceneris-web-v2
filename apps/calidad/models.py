# calidad/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from datetime import timedelta



# ==============================================================================
# 1. MODELOS MAESTROS O DE CONFIGURACIÓN
# ==============================================================================
   

class Clinica(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de Contacto")
    email_contacto = models.EmailField(blank=True, null=True, verbose_name="Email de Contacto")
    persona_contacto = models.CharField(max_length=150, blank=True, null=True, verbose_name="Persona de Contacto")
    imagen_fachada = models.ImageField(
        upload_to='clinicas/fachadas/',
        blank=True,
        null=True,
        verbose_name="Imagen de fachada"
    )
    google_maps_url = models.URLField(blank=True, null=True, verbose_name="Link de ubicación en Google Maps")

    def __str__(self):
        return self.nombre


class ArchivoClinica(models.Model):
    """
    Modelo para gestionar PDFs adjuntos por clínica
    (recomendaciones pre-examen, protocolos, etc.)
    """
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='archivos_adjuntos', verbose_name="Clínica")
    descripcion = models.CharField(max_length=100, help_text="Ej: Recomendaciones pre-examen, Protocolo de ayuno, etc.")
    archivo_pdf = models.FileField(upload_to='clinicas/recomendaciones/', verbose_name="Archivo PDF")
    activo = models.BooleanField(default=True, help_text="Marcar desactivo para dejar de enviarlo")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Archivos de Clínicas"
        ordering = ['-fecha_carga']
    
    def __str__(self):
        return f"{self.clinica.nombre} - {self.descripcion}"
dni_validator = RegexValidator(
    regex=r'^\d{8}$',
    message='El DNI debe tener exactamente 8 dígitos numéricos.'
)

# ==============================================================================
# 3. MODELOS DE SEGUIMIENTO (Relacionados con EMO)
# ==============================================================================
class EMO(models.Model):
    ESTADO_CHOICES = [('Programado', 'Programado'), ('Realizado', 'Realizado')]
    APTITUD_CHOICES = [('Pendiente', 'Pendiente'), ('Apto', 'Apto'), ('Apto con Restricción', 'Apto con Restricción'), ('Observado', 'Observado'), ('No Apto', 'No Apto')]
    TIPO_EMO_CHOICES = [('Periodico', 'Periódico'), ('Retiro', 'Retiro'), ('Preocupacional', 'Preocupacional'), ('Complementario', 'Complementario')]

    trabajador = models.ForeignKey('recursoshumanos.Trabajador', on_delete=models.CASCADE, related_name='historial_emo')
    empresa = models.ForeignKey('recursoshumanos.Empresa', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Empresa")
    proyecto = models.ForeignKey('recursoshumanos.Proyecto', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proyecto Asociado")
    subproyecto = models.ForeignKey('recursoshumanos.Proyecto', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Subproyecto", related_name='emos_subproyecto')
    cargo = models.ForeignKey('recursoshumanos.Cargo', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Puesto / Cargo")
    lugar_examen = models.ForeignKey(Clinica, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Clínica / Hospital")
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Programado')
    fecha_programada = models.DateField(null=True, blank=True)
    hora_examen = models.TimeField(null=True, blank=True, verbose_name="Hora del Examen", help_text="Hora programada para realizar el examen")
    tipo_emo = models.CharField(max_length=100, choices=TIPO_EMO_CHOICES)
    
    fecha_realizacion = models.DateField(null=True, blank=True)
    aptitud = models.CharField(max_length=50, choices=APTITUD_CHOICES, default='Pendiente')
    restriccion = models.TextField(blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    archivo_pdf = models.FileField(upload_to='emos_pdf/', blank=True, null=True, verbose_name="PDF Principal")
    
    archivo_subsana = models.FileField(upload_to='subsana_pdf/', blank=True, null=True, verbose_name="PDF de Subsanación")
    subsana_validado = models.BooleanField(default=False)
    fecha_validacion_subsana = models.DateTimeField(null=True, blank=True)
    
    confirmado_por_habilitador = models.BooleanField(default=False)
    fecha_confirmacion = models.DateField(null=True, blank=True)
    confirmado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='emos_confirmados')
    archivo_confirmacion = models.FileField(upload_to='confirmaciones_pdf/', blank=True, null=True, verbose_name="PDF de Confirmación de Lectura")

    @property
    def esta_vencido(self):
        """Devuelve True si el EMO tiene una fecha de vencimiento y ya pasó."""
        if not self.fecha_vencimiento:
            return False # No puede estar vencido si no tiene fecha de vencimiento
        return self.fecha_vencimiento < timezone.now().date()

    @property
    def esta_por_vencer(self, dias=30):
        """Devuelve True si el EMO vence en los próximos 'dias'."""
        if not self.fecha_vencimiento:
            return False
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=dias)
        # Debe estar en el futuro, pero dentro del rango de los próximos 30 días.
        return hoy <= self.fecha_vencimiento <= limite

    @property
    def esta_vigente(self):
        """Devuelve True si el EMO no está vencido ni por vencer."""
        if not self.fecha_vencimiento:
            return False
        # Para que sea "vigente" (en el sentido de no necesitar atención inmediata),
        # no debe estar vencido NI por vencer.
        return not self.esta_vencido and not self.esta_por_vencer

    def __str__(self):
        return f"EMO de {self.trabajador} ({self.get_tipo_emo_display()})"

class Control(models.Model):
    emo = models.ForeignKey(EMO, on_delete=models.CASCADE, related_name='controles')
    fecha_programada = models.DateField()
    descripcion = models.CharField(max_length=255)
    archivo_adjunto = models.FileField(upload_to='controles_pdf/', blank=True, null=True)
    realizado = models.BooleanField(default=False)
    fecha_realizacion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Control para EMO #{self.emo.id} - {self.descripcion}"

class ArchivoAdjuntoEMO(models.Model):
    emo = models.ForeignKey(EMO, on_delete=models.CASCADE, related_name='archivos_adjuntos')
    descripcion = models.CharField(max_length=100)
    archivo = models.FileField(upload_to='emos_adjuntos/')

    def __str__(self):
        return f"Adjunto para EMO de {self.emo.trabajador}"

# NOTA: He eliminado el modelo 'Producto' que parecía ser de una app 'inventario' de prueba.
# Si todavía lo necesitas, puedes volver a añadirlo.
