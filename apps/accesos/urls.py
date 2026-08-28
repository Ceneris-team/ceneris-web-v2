from django.urls import path
from . import views

app_name = 'accesos'

urlpatterns = [
    path('portal/', views.dashboard_seleccion, name='dashboard_seleccion'),

    # CAV-187 (mejora): lo consulta el vigilante de sesion unica (sin login).
    path('estado-sesion/', views.estado_sesion, name='estado_sesion'),
    path('directorio-trabajadores/', views.lista_trabajadores, name='lista_trabajadores'),
    
    # RUTAS DE USUARIOS
    path('lista-usuarios/', views.lista_usuarios_sistema, name='lista_usuarios'),
    path('usuarios/eliminar/<int:user_id>/', views.eliminar_usuario_sistema, name='eliminar_usuario_sistema'),
    path('crear-credenciales/', views.crear_credenciales, name='crear_credenciales'),
    
    # OTRAS RUTAS
    path('editar-permisos/', views.editar_permisos, name='editar_permisos'),
    path('resetear-password/', views.resetear_password, name='resetear_password'),
    path('toggle-estado-usuario/<int:user_id>/', views.toggle_estado_usuario, name='toggle_estado_usuario'),
    path('editar-datos-trabajador/', views.editar_datos_trabajador, name='editar_datos_trabajador'),

    # RUTA PARA CREAR ACCESO SIN VINCULO DE TRABAJADOR
    path('usuarios/crear-externo/', views.crear_usuario_externo, name='crear_usuario_externo'),

    # NUEVAS RUTAS PARA ROLES
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/crear/', views.crear_rol, name='crear_rol'),
    path('roles/editar/<int:rol_id>/', views.editar_rol, name='editar_rol'),
    path('roles/eliminar/<int:rol_id>/', views.eliminar_rol, name='eliminar_rol'),
]
