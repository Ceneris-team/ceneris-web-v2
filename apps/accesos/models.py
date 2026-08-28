from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# Texto unico del aviso: lo usan el modal del navegador desplazado y el
# banner del login, para que el usuario lea siempre lo mismo.
MENSAJE_SESION_DUPLICADA = (
    'Tu sesión se cerró porque se inició sesión con esta misma cuenta '
    'desde otro dispositivo. Por seguridad, solo puede haber una sesión '
    'activa a la vez.'
)


class SesionCerradaRemotamente(models.Model):
    """
    CAV-187 (mejora): deja constancia de cada sesion web que fue cerrada porque
    la misma cuenta inicio sesion desde otro dispositivo (regla de
    sesion unica de CAV-187).

    El registro se consulta despues, cuando el navegador que perdio la
    sesion vuelve a hablar con el servidor, para poder explicarle al
    usuario por que se le cerro la cuenta en vez de dejarlo en un login
    sin ninguna explicacion.
    """

    MOTIVO_SESION_DUPLICADA = 'sesion_duplicada'

    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sesiones_cerradas_remotamente',
    )
    fecha_cierre = models.DateTimeField(default=timezone.now)
    ip_nuevo_dispositivo = models.GenericIPAddressField(null=True, blank=True)
    user_agent_nuevo = models.CharField(max_length=300, blank=True, default='')
    avisado = models.BooleanField(
        default=False,
        help_text='Se marca cuando el usuario ya vio el aviso del cierre.',
    )

    class Meta:
        verbose_name = 'sesion cerrada remotamente'
        verbose_name_plural = 'sesiones cerradas remotamente'
        ordering = ['-fecha_cierre']

    def __str__(self):
        return f'{self.usuario.username} - {self.fecha_cierre:%d/%m/%Y %H:%M}'

    @classmethod
    def registrar(cls, session_key, usuario, ip=None, user_agent=''):
        """Guarda (o refresca) el aviso pendiente para una session_key."""
        return cls.objects.update_or_create(
            session_key=session_key,
            defaults={
                'usuario': usuario,
                'fecha_cierre': timezone.now(),
                'ip_nuevo_dispositivo': ip,
                'user_agent_nuevo': (user_agent or '')[:300],
                'avisado': False,
            },
        )[0]

    @classmethod
    def purgar_antiguas(cls, dias=7):
        """Limpia avisos viejos; su cookie ya no le sirve a nadie."""
        limite = timezone.now() - timedelta(days=dias)
        cls.objects.filter(fecha_cierre__lt=limite).delete()

    @classmethod
    def aviso_pendiente(cls, session_key):
        """Devuelve el aviso sin mostrar de esa session_key, o None."""
        if not session_key:
            return None
        return cls.objects.filter(session_key=session_key, avisado=False).first()
