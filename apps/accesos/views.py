from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe
from recursoshumanos.models import Trabajador
from django.contrib.auth.models import Permission
from django.db.models import Count


def tiene_permiso_metricas(user):
    """
    Valida que el usuario tenga AMBOS grupos: 'Administrador' y 'Metricas'.
    Ignoramos si es superusuario (según tu pedido).
    """
    # Obtenemos los grupos del usuario
    grupos = user.groups.values_list('name', flat=True)
    
    # Debe tener "Administrador" Y "Metricas"
    return 'Administrador' in grupos and 'Metricas' in grupos


@login_required
def dashboard_seleccion(request):
    # 1. Obtenemos los nombres de los grupos como una lista de texto
    grupos = list(request.user.groups.values_list('name', flat=True))
    
    # 2. Imprimimos en la consola negra para depurar (mira tu terminal)
    print(f"GRUPOS DETECTADOS: {grupos}") 

    # 3. Verificar si tiene trabajador asociado
    tiene_trabajador = False
    try:
        if request.user.trabajador:
            tiene_trabajador = True
    except:
        pass

    # 4. Enviamos 'user_groups' al template
    return render(request, 'accesos/dashboard_seleccion.html', {
        'user_groups': grupos,
        'tiene_trabajador': tiene_trabajador
    })

# Gestion de usuarios
@login_required
@user_passes_test(tiene_permiso_metricas)
def gestion_usuarios(request):
    """
    Vista maestra de gestión de trabajadores y sus accesos.
    """
    # Consulta Optimizada: Traemos trabajador + User + Grupos + Área
    # Esto evita hacer 100 consultas si hay 100 trabajadores.
    trabajadores = Trabajador.objects.all().select_related(
        'user', 'area'
    ).prefetch_related(
        'user__groups'
    ).order_by('apellido_paterno')

    # Traemos todos los grupos para el Modal de Edición
    grupos_disponibles = Group.objects.all().order_by('name')

    # Métricas rápidas para el dashboard
    total_trabajadores = trabajadores.count()
    total_con_acceso = sum(1 for t in trabajadores if t.user)
    
    context = {
        'trabajadores': trabajadores,
        'grupos_disponibles': grupos_disponibles,
        'stats': {
            'total': total_trabajadores,
            'con_acceso': total_con_acceso,
            'sin_acceso': total_trabajadores - total_con_acceso
        }
    }
    return render(request, 'accesos/gestion_usuarios.html', context)


@login_required
def crear_credenciales(request):
    if request.method == 'POST':
        trabajador_id = request.POST.get('trabajador_id')
        username_manual = request.POST.get('username_manual', '').strip()
        password_manual = request.POST.get('password_manual', '')
        grupos_ids = request.POST.getlist('grupos')

        trabajador = get_object_or_404(Trabajador, id=trabajador_id)

        # Validaciones
        if not username_manual or not password_manual or not password_manual.strip():
            messages.error(request, "Usuario y contraseña son obligatorios.")
            return redirect('accesos:lista_trabajadores')

        if User.objects.filter(username=username_manual).exists():
            messages.error(request, f"El usuario '{username_manual}' ya existe. Elige otro.")
            return redirect('accesos:lista_trabajadores')

        if trabajador.user:
            messages.warning(request, "Este trabajador ya tiene usuario asignado.")
            return redirect('accesos:lista_trabajadores')

        try:
            # Crear usuario
            nuevo_usuario = User.objects.create_user(
                username=username_manual,
                password=password_manual,
                email=trabajador.email or '',
                first_name=trabajador.nombres,
                last_name=f"{trabajador.apellido_paterno} {trabajador.apellido_materno}"
            )

            # Asignar grupos
            if grupos_ids:
                nuevo_usuario.groups.set(grupos_ids)

            # Vincular al trabajador
            trabajador.user = nuevo_usuario
            trabajador.save()

            messages.success(request, f"Usuario creado exitosamente: {username_manual}")

        except Exception as e:
            messages.error(request, f"Error al crear usuario: {str(e)}")

    return redirect('accesos:lista_trabajadores')

@login_required
def editar_permisos(request):
    if request.method == 'POST':
        # CORRECCIÓN: Ahora recibimos 'user_id' directamente desde el modal
        user_id = request.POST.get('user_id') 
        grupos_seleccionados = request.POST.getlist('grupos')
        
        # Buscamos el Usuario (User), no el Trabajador
        user = get_object_or_404(User, id=user_id)
        
        try:
            user.groups.clear()
            for group_id in grupos_seleccionados:
                grupo = Group.objects.get(id=group_id)
                user.groups.add(grupo)
            
            messages.success(request, f"Roles actualizados para {user.username}.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        
    return redirect('accesos:lista_usuarios')


@login_required
def resetear_password(request):
    """
    Recibe un POST con el ID del usuario y (opcionalmente) una contraseña manual.
    """
    if request.method == 'POST':
        # CORRECCIÓN: Recibimos user_id
        user_id = request.POST.get('user_id')
        password_manual = request.POST.get('password_manual')
        
        # Validar permisos
        grupos = request.user.groups.values_list('name', flat=True)
        if not (request.user.is_superuser or 'Administrador' in grupos or 'Metricas' in grupos):
             messages.error(request, "No tienes permisos.")
             return redirect('accesos:lista_usuarios')

        # Buscamos el Usuario directamente
        user = get_object_or_404(User, id=user_id)

        try:
            if password_manual and len(password_manual.strip()) > 0:
                nuevo_password = password_manual
                tipo_msg = "Manual"
            else:
                nuevo_password = get_random_string(length=10)
                tipo_msg = "Aleatoria"
            
            user.set_password(nuevo_password)
            user.save()

            mensaje_html = f"""
            <div class="flex flex-col gap-2">
                <div class="border-b border-orange-200 pb-1">
                    <strong class="text-orange-700">Contraseña Restablecida ({tipo_msg})</strong>
                </div>
                <div>
                    Usuario: <span class="font-bold">{user.username}</span><br>
                    Nueva Clave: <span class="font-mono bg-yellow-100 px-2 py-1 rounded text-lg font-bold select-all">{nuevo_password}</span>
                </div>
            </div>
            """
            messages.success(request, mark_safe(mensaje_html))

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return redirect('accesos:lista_usuarios')

@login_required
def gestion_trabajadores(request):
    """
    Muestra la LISTA MAESTRA de todos los trabajadores y su estado de acceso.
    """
    # 1. Validar permisos (Solo Admin o Metricas/RRHH con permisos especiales)
    # Ajusta esta lógica según tus grupos
    grupos = request.user.groups.values_list('name', flat=True)
    if not (request.user.is_superuser or 'Administrador' in grupos or 'Metricas' in grupos):
        return render(request, 'metricas_ceneris/error.html', {'mensaje': 'Acceso denegado'})

    # 2. Consulta OPTIMIZADA (Trae todo de una vez)
    # select_related: Trae datos de tablas relacionadas (User, Area)
    # prefetch_related: Trae los grupos (relación muchos a muchos)
    trabajadores = Trabajador.objects.all().select_related(
        'user', 'area'
    ).prefetch_related(
        'user__groups'
    ).order_by('apellido_paterno')

    # 3. Datos para los Modales
    grupos_disponibles = Group.objects.all().order_by('name')

    # 4. Estadísticas rápidas
    total = trabajadores.count()
    con_usuario = sum(1 for t in trabajadores if t.user)
    
    context = {
        'trabajadores': trabajadores, # <--- ESTA ES LA LISTA COMPLETA
        'grupos_disponibles': grupos_disponibles,
        'stats': {
            'total': total,
            'activos': con_usuario,
            'pendientes': total - con_usuario
        }
    }
    return render(request, 'accesos/gestion_usuarios.html', context)

@login_required
def lista_trabajadores(request):
    """
    Vista enfocada en el PERSONAL.
    Muestra todos los trabajadores y permite CREAR cuentas a quienes no tienen.
    """
    # Traemos todos los trabajadores + info si tienen usuario
    trabajadores = Trabajador.objects.all().select_related('user', 'area').order_by('apellido_paterno')
    
    # Necesitamos los grupos solo para el modal de creación
    grupos_disponibles = Group.objects.all().order_by('name')

    return render(request, 'accesos/lista_trabajadores.html', {
        'trabajadores': trabajadores,
        'grupos_disponibles': grupos_disponibles
    })

@login_required
def lista_usuarios_sistema(request):
    """
    Vista enfocada en SEGURIDAD.
    Muestra solo los USUARIOS (auth_user) activos en el sistema.
    Permite editar roles, resetear claves y desactivar cuentas.
    """
    # Traemos usuarios que estén vinculados a un trabajador (o todos si prefieres)
    # Filtramos usuarios que no son superusers para no bloquearte a ti mismo por error
    usuarios = User.objects.filter(is_superuser=False).select_related('trabajador').prefetch_related('groups').order_by('username')
    
    grupos_disponibles = Group.objects.all().order_by('name')

    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios,
        'grupos_disponibles': grupos_disponibles
    })

@login_required
def eliminar_usuario_sistema(request, user_id):
    usuario_a_eliminar = get_object_or_404(User, id=user_id)

    # 1. Seguridad: No puedes eliminarte a ti mismo
    if usuario_a_eliminar == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta mientras estás logueado.")
        return redirect('accesos:lista_usuarios')

    # 2. Seguridad: Evitar borrar superusuarios desde esta vista (opcional, pero recomendado)
    if usuario_a_eliminar.is_superuser:
        messages.error(request, "No se pueden eliminar superusuarios desde este panel.")
        return redirect('accesos:lista_usuarios')

    # 3. Proceder a eliminar
    nombre_usuario = usuario_a_eliminar.username
    usuario_a_eliminar.delete()
    
    messages.success(request, f"El usuario '{nombre_usuario}' ha sido eliminado correctamente.")
    return redirect('accesos:lista_usuarios')



# AGREGAR ESTA PEQUEÑA FUNCIÓN EXTRA ÚTIL
@login_required
def toggle_estado_usuario(request, user_id):
    """Activa o desactiva un usuario sin borrarlo"""
    user = get_object_or_404(User, id=user_id)
    if not request.user.is_superuser and not request.user.groups.filter(name='Administrador').exists():
         return redirect('accesos:lista_usuarios')
         
    user.is_active = not user.is_active
    user.save()
    estado = "activado" if user.is_active else "suspendido"
    messages.success(request, f"Usuario {user.username} {estado} correctamente.")
    return redirect('accesos:lista_usuarios')

@login_required
def editar_datos_trabajador(request):
    """
    Edita datos básicos del trabajador (Email, Teléfono) desde el panel de accesos.
    """
    if request.method == 'POST':
        trabajador_id = request.POST.get('trabajador_id')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        # Si quieres permitir editar el área aquí también:
        # area_id = request.POST.get('area') 
        
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        
        try:
            trabajador.email = email
            trabajador.telefono = telefono
            trabajador.save()
            
            # Si el trabajador tiene usuario vinculado, actualizamos también el email del User
            if trabajador.user:
                trabajador.user.email = email
                trabajador.user.save()

            messages.success(request, f"Datos actualizados para {trabajador.nombres}.")
        except Exception as e:
            messages.error(request, f"Error al actualizar: {str(e)}")
            
    return redirect('accesos:lista_trabajadores')

@login_required
def lista_roles(request):
    """
    Muestra la lista de roles (Grupos de Django) existentes y permite crear nuevos.
    """
    # Excluimos grupos automáticos si los tuvieras, o mostramos todos
    roles = Group.objects.annotate(num_usuarios=Count('user')).order_by('name')
    
    # Traemos todos los permisos del sistema para el modal de creación/edición
    # Filtramos permisos de las apps principales para no saturar
    permisos = Permission.objects.select_related('content_type').filter(
        content_type__app_label__in=['recursoshumanos', 'calidad', 'administracion', 'cotizaciones'] 
    ).order_by('content_type__model', 'name')

    return render(request, 'roles/lista_roles.html', {
        'roles': roles,
        'permisos': permisos
    })

@login_required
def crear_rol(request):
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol')
        permisos_ids = request.POST.getlist('permisos') # Lista de IDs seleccionados

        if nombre_rol:
            if Group.objects.filter(name=nombre_rol).exists():
                messages.error(request, f"El rol '{nombre_rol}' ya existe.")
            else:
                nuevo_grupo = Group.objects.create(name=nombre_rol)
                if permisos_ids:
                    nuevo_grupo.permissions.set(permisos_ids)
                messages.success(request, f"Rol '{nombre_rol}' creado exitosamente.")
        else:
            messages.warning(request, "El nombre del rol es obligatorio.")
            
    return redirect('accesos:lista_roles')

@login_required
def eliminar_rol(request, rol_id):
    rol = get_object_or_404(Group, id=rol_id)
    # Evitar borrar roles críticos si es necesario
    if rol.name in ['Administrador', 'Superusuario']:
        messages.error(request, "No se puede eliminar este rol crítico.")
    else:
        rol.delete()
        messages.success(request, "Rol eliminado correctamente.")
    return redirect('accesos:lista_roles')

@login_required
def editar_rol(request, rol_id):
    """
    Edita el nombre y los permisos de un rol existente.
    """
    rol = get_object_or_404(Group, id=rol_id)
    
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol')
        permisos_ids = request.POST.getlist('permisos')

        if nombre_rol:
            # Validar que no exista otro con el mismo nombre (excluyendo el actual)
            if Group.objects.filter(name=nombre_rol).exclude(id=rol.id).exists():
                messages.error(request, f"El nombre '{nombre_rol}' ya está en uso.")
            else:
                rol.name = nombre_rol
                rol.save()
                
                # Actualizar permisos (set reemplaza los anteriores)
                if permisos_ids:
                    rol.permissions.set(permisos_ids)
                else:
                    rol.permissions.clear()
                    
                messages.success(request, f"Rol '{nombre_rol}' actualizado correctamente.")
        else:
            messages.warning(request, "El nombre no puede estar vacío.")
            
    return redirect('accesos:lista_roles')

def actualizar_flags_trabajador(trabajador, grupos_asignados):
    """
    Función auxiliar para actualizar los checks de Jefe/Gerente
    según los roles que tenga el usuario.
    """
    if not trabajador:
        return

    # Convertimos a lista de nombres para verificar
    nombres_roles = [g.name.lower() for g in grupos_asignados]
    
    es_jefe = False
    es_gerente = False

    # Lógica de detección (puedes ajustar los nombres exactos)
    for nombre in nombres_roles:
        if 'jefe' in nombre or 'supervisores' in nombre:
            es_jefe = True
        if 'gerente' in nombre or 'gerencia' in nombre:
            es_gerente = True
    
    # Actualizamos el trabajador
    trabajador.es_jefe = es_jefe
    trabajador.es_gerente = es_gerente
    trabajador.save(update_fields=['es_jefe', 'es_gerente'])

@login_required
def crear_usuario_externo(request):
    """
    Crea un usuario de sistema puro (Admin, Auditor, Soporte) 
    sin vincularlo a un Trabajador (RRHH).
    """
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        grupos_ids = request.POST.getlist('grupos')

        # Validaciones básicas
        if not username or not password:
            messages.error(request, "El usuario y la contraseña son obligatorios.")
            return redirect('accesos:lista_usuarios')

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('accesos:lista_usuarios')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"El nombre de usuario '{username}' ya está en uso.")
            return redirect('accesos:lista_usuarios')

        try:
            # Crear usuario
            nuevo_usuario = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Asignar roles
            if grupos_ids:
                nuevo_usuario.groups.set(grupos_ids)

            messages.success(request, f"Usuario externo '{username}' creado exitosamente.")

        except Exception as e:
            messages.error(request, f"Error al crear usuario: {str(e)}")

    return redirect('accesos:lista_usuarios')