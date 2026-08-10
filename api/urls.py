from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

# Importaciones de vistas de la API
from .views import (
    MyTokenObtainPairView,
    EstadoTrabajadorView,
    actualizar_email,
    actualizar_telefono,
    cambiar_contrasena,
    RegistrarAsistenciaView,
    SolicitudHorasExtraCreateAPIView,
    ListarFaltasView,
    CrearJustificacionView,
    ListarMisSolicitudesHEView,
    HistorialAsistenciaView,
    ListarMarcacionesLogView,
    actualizar_nombre
)

urlpatterns = [
    # --- RUTAS DE AUTENTICACIÓN JWT ---
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # --- RUTAS DE USUARIO ---
    path('cambiar-password/', cambiar_contrasena, name='cambiar-password-legacy'),
    path('usuario/cambiar-contrasena/', cambiar_contrasena, name='cambiar-contrasena'),
    path('actualizar-nombre/', actualizar_nombre, name='actualizar_nombre'),
    path('actualizar-email/', actualizar_email, name='actualizar_email'),
    path('actualizar-telefono/', actualizar_telefono, name='actualizar_telefono'),
    
    # --- RUTAS DE ASISTENCIA ---
    path('trabajador/estado/', EstadoTrabajadorView.as_view(), name='trabajador-estado'),
    path('asistencias/registrar/', RegistrarAsistenciaView.as_view(), name='registrar-asistencia'),
    path('asistencias/log/', ListarMarcacionesLogView.as_view(), name='log-asistencias'),
    path('historial-asistencia/', HistorialAsistenciaView.as_view(), name='historial-asistencia'),
    
    # --- RUTAS DE FALTAS Y JUSTIFICACIONES ---
    path('faltas/pendientes/', ListarFaltasView.as_view(), name='listar-faltas'),
    path('justificaciones/crear/', CrearJustificacionView.as_view(), name='crear-justificacion'),
    
    # --- RUTAS DE HORAS EXTRA ---
    path('horas-extra/solicitar/', SolicitudHorasExtraCreateAPIView.as_view(), name='solicitar-horas-extra'),
    path('horas-extra/mis-solicitudes/', ListarMisSolicitudesHEView.as_view(), name='mis-solicitudes-he'),
]