from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def invalidar_sesiones_anteriores(sender, request, user, **kwargs):
    """
    CAV-187: un usuario no-administrador no puede tener mas de una
    sesion web activa a la vez. Al loguearse, se borran las demas
    sesiones (de otros navegadores/dispositivos) de este mismo usuario.

    Solo aplica al login por sesion (web). El login movil usa JWT sin
    estado y no pasa por esta señal.
    """
    if user.is_superuser:
        # Regla critica de negocio: el superusuario nunca pierde sus
        # sesiones activas por este bloqueo.
        return

    current_key = request.session.session_key
    sesiones_activas = Session.objects.filter(expire_date__gte=timezone.now())

    for sesion in sesiones_activas:
        if sesion.session_key == current_key:
            continue
        data = sesion.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.pk):
            sesion.delete()
