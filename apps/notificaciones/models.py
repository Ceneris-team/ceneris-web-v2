from django.db import models
from django.utils import timezone


class PlantillaEmail(models.Model):
    """Plantilla de correo reutilizable con variables parametrizadas."""
    nombre = models.CharField(max_length=100, unique=True)
    asunto = models.CharField(
        max_length=255,
        help_text='Puede usar variables con {{ variable }}. Ej: "Bienvenido {{ nombre }}"',
    )
    cuerpo_html = models.TextField(
        help_text='HTML del correo. Use {{ variable }} para valores dinámicos.',
    )
    cuerpo_texto = models.TextField(
        blank=True,
        help_text='Versión texto plano (fallback). Dejar vacío para auto-generar.',
    )
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plantilla de Email'
        verbose_name_plural = 'Plantillas de Email'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class EmailLog(models.Model):
    """Registro de cada envío de correo con soporte para reintentos."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ENVIADO = 'enviado', 'Enviado'
        FALLIDO = 'fallido', 'Fallido'
        REINTENTANDO = 'reintentando', 'Reintentando'
        DESCARTADO = 'descartado', 'Descartado (máx. reintentos)'

    destinatario = models.EmailField()
    cc = models.TextField(blank=True, help_text='Direcciones CC separadas por coma')
    bcc = models.TextField(blank=True, help_text='Direcciones BCC separadas por coma')
    asunto = models.CharField(max_length=255)
    cuerpo_html = models.TextField()
    cuerpo_texto = models.TextField(blank=True)
    remitente = models.EmailField(blank=True)

    plantilla = models.ForeignKey(
        PlantillaEmail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
    )
    contexto_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Variables de contexto usadas para renderizar la plantilla',
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )
    intentos = models.PositiveSmallIntegerField(default=0)
    max_intentos = models.PositiveSmallIntegerField(default=5)
    proximo_reintento = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.TextField(blank=True)

    sendgrid_message_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    enviado_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Log de Email'
        verbose_name_plural = 'Logs de Email'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado', 'proximo_reintento']),
        ]

    def __str__(self):
        return f'{self.asunto} → {self.destinatario} [{self.estado}]'

    def calcular_proximo_reintento(self):
        """Backoff exponencial: 1min, 2min, 4min, 8min, 16min."""
        delay_seconds = 60 * (2 ** self.intentos)
        self.proximo_reintento = timezone.now() + timezone.timedelta(seconds=delay_seconds)
