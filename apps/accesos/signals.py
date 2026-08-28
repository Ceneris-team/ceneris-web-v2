from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone

from .models import SesionCerradaRemotamente


def _ip_cliente(request):
    """IP del dispositivo que acaba de iniciar sesion (respeta el proxy)."""
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if reenviada:
        return reenviada.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


@receiver(user_logged_in)
def invalidar_sesiones_anteriores(sender, request, user, **kwargs):
    """
    CAV-187: un usuario no-administrador no puede tener mas de una
    sesion web activa a la vez. Al loguearse, se borran las demas
    sesiones (de otros navegadores/dispositivos) de este mismo usuario.

    CAV-187 (mejora): antes de borrar cada sesion se guarda un aviso
    (SesionCerradaRemotamente) para que el dispositivo desplazado pueda
    explicarle al usuario por que perdio la sesion.

    Solo aplica al login por sesion (web). El login movil usa JWT sin
    estado y no pasa por esta señal.
    """
    if user.is_superuser and getattr(settings, 'SESION_UNICA_EXIMIR_SUPERUSUARIO', True):
        # Regla critica de negocio: el superusuario nunca pierde sus
        # sesiones activas por este bloqueo.
        return

    current_key = request.session.session_key
    ip = _ip_cliente(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    sesiones_activas = Session.objects.filter(expire_date__gte=timezone.now())

    for sesion in sesiones_activas:
        if sesion.session_key == current_key:
            continue
        data = sesion.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.pk):
            SesionCerradaRemotamente.registrar(
                session_key=sesion.session_key,
                usuario=user,
                ip=ip,
                user_agent=user_agent,
            )
            sesion.delete()

    # El aviso solo sirve mientras la cookie vieja siga viva; despues
    # es basura que no queremos acumular en la tabla.
    SesionCerradaRemotamente.purgar_antiguas()
