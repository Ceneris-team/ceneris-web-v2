# api/views.py
# Archivo centralizado para todas las vistas API REST

from django.shortcuts import render
from rest_framework import generics, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from datetime import datetime, timedelta, time, date
from decimal import Decimal
import pytz
import json
import hashlib

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# Importaciones de modelos
from recursoshumanos.models import (
    SolicitudHorasExtra, Trabajador, Dispositivo, Asistencia, 
    Justificacion, TareoDiario, IntentoFraude
)

# Importaciones de serializers
from .serializers import (
    MyTokenObtainPairSerializer, AsistenciaSerializer,
    FaltaPendienteSerializer, CrearJustificacionSerializer,
    SolicitudHorasExtraSerializer, UsuarioAutorizadoSerializer
)

# Importaciones de servicios
from recursoshumanos.services import recalcular_asistencia_diaria
from admin_panel.settings import db

# Constantes
TARDANZA_MINIMA_HORAS = Decimal('0.25')
TOLERANCIA_TARDANZA_MINUTOS = 3
LOCAL_TIMEZONE = pytz.timezone('America/Lima')


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'si', 'on'}
    return False


def _registrar_intento_fraude(request, reason, trabajador=None):
    """Registra un intento bloqueado en SQL y en Firestore para alimentar dashboard y listado de fraudes."""
    try:
        def _to_float(value):
            try:
                return float(value) if value not in (None, '') else None
            except (TypeError, ValueError):
                return None

        payload = {
            'timestamp': timezone.now(),
            'reason': reason,
            'blockedReason': reason,
            'status': 'BLOCKED',
            'source': 'api_registrar_asistencia',
            'userName': '',
            'userDni': '',
            'deviceId': request.data.get('device_id') or request.data.get('deviceId') or '',
            'locationName': request.data.get('locationName') or request.data.get('nombre_ubicacion') or '',
            'reportedLatitude': request.data.get('reportedLatitude') or request.data.get('latitude') or request.data.get('lat'),
            'reportedLongitude': request.data.get('reportedLongitude') or request.data.get('longitude') or request.data.get('lng'),
            'securityReason': request.data.get('securityReason') or request.data.get('motivoBloqueo') or request.data.get('blockedReason') or reason,
            'isFraud': True,
        }

        if trabajador is not None:
            payload['userName'] = trabajador.nombre_completo
            payload['userDni'] = trabajador.dni
        elif request.user.is_authenticated:
            payload['userName'] = request.user.get_full_name() or request.user.username

        # Conserva campos relevantes enviados por app, por si cambian contratos.
        for key in ['appVersion', 'platform', 'ipAddress', 'is_mock_location', 'is_rooted', 'is_emulator']:
            if key in request.data:
                payload[key] = request.data.get(key)

        # 1) Guardado local (SQL): fuente de respaldo y consulta estable.
        try:
            IntentoFraudeAsistencia.objects.create(
                timestamp=payload['timestamp'],
                user_name=payload.get('userName') or '',
                user_dni=payload.get('userDni') or '',
                reason=payload.get('reason') or '',
                blocked_reason=payload.get('blockedReason') or '',
                security_reason=payload.get('securityReason') or '',
                device_id=payload.get('deviceId') or '',
                location_name=payload.get('locationName') or '',
                reported_latitude=_to_float(payload.get('reportedLatitude')),
                reported_longitude=_to_float(payload.get('reportedLongitude')),
                source=payload.get('source') or 'api_registrar_asistencia',
                raw_payload=payload,
            )
        except Exception as sql_exc:
            print(f"⚠️ No se pudo registrar intento de fraude en SQL: {sql_exc}")

        # 2) Guardado en Firestore (si está disponible).
        try:
            db.collection('asistencias_fraudulentas').add(payload)
        except Exception as fs_exc:
            print(f"⚠️ No se pudo registrar intento de fraude en Firestore: {fs_exc}")
    except Exception as log_exc:
        print(f"⚠️ No se pudo registrar intento de fraude: {log_exc}")


class SolicitudHorasExtraCreateAPIView(generics.CreateAPIView):
    queryset = SolicitudHorasExtra.objects.all()
    serializer_class = SolicitudHorasExtraSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        try:
            trabajador = Trabajador.objects.get(user=self.request.user)
            solicitud = serializer.save(trabajador=trabajador)
        except Trabajador.DoesNotExist:
            raise serializers.ValidationError("El usuario no tiene un Trabajador asignado.")

        try:
            from notificaciones.notificadores import notificar_solicitud_horas_extra
            notificar_solicitud_horas_extra(solicitud, request=self.request)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                'No se pudo enviar notificación de solicitud #%s: %s',
                solicitud.pk, exc,
            )

    # --- AQUI ESTA LA MAGIA DEL DEBUG ---
    def create(self, request, *args, **kwargs):
        print("\n" + "="*50)
        print("🚨 DEBUG: INICIO DE SOLICITUD DE HORAS EXTRA")
        print(f"👤 Usuario autenticado: {request.user.username}")
        
        # 1. Ver qué datos llegaron realmente desde Flutter
        print(f"📦 Datos recibidos (request.data): {json.dumps(request.data, indent=2)}")

        serializer = self.get_serializer(data=request.data)
        
        # 2. Validar y si falla, IMPRIMIR EL ERROR
        if not serializer.is_valid():
            print("❌ ERROR DE VALIDACIÓN:")
            print(json.dumps(serializer.errors, indent=2)) # Esto nos dirá EXACTAMENTE qué campo falla
            print("="*50 + "\n")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Intentar guardar (ejecuta perform_create)
        try:
            self.perform_create(serializer)
        except Exception as e:
            print(f"❌ ERROR AL GUARDAR (perform_create): {str(e)}")
            print("="*50 + "\n")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Éxito
        headers = self.get_success_headers(serializer.data)
        print("✅ SOLICITUD CREADA CON ÉXITO")
        print("="*50 + "\n")
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class EstadoTrabajadorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        usuario = request.user
        lima_tz = pytz.timezone('America/Lima')
        ahora_lima = datetime.now(lima_tz)
        hoy_fecha = ahora_lima.date()

        # 1. Obtener Trabajador
        try:
            trabajador = Trabajador.objects.prefetch_related('ubicaciones_permitidas').get(user=usuario)
        except Trabajador.DoesNotExist:
            return Response({"error": "Sin perfil"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Última marcación
        ultimo_tipo = "Salida"
        try:
            inicio = lima_tz.localize(datetime.combine(hoy_fecha, time.min))
            fin = lima_tz.localize(datetime.combine(hoy_fecha, time.max))
            asist = Asistencia.objects.filter(usuario=usuario, timestamp__range=(inicio, fin)).order_by('-timestamp').first()
            if asist: ultimo_tipo = asist.tipo_marcacion
        except: pass

        # 3. Ubicaciones
        ubicaciones_json = [{'id': u.pk, 'nombre': u.nombre, 'latitud': u.latitud, 'longitud': u.longitud, 'radio': u.radio} for u in trabajador.ubicaciones_permitidas.all()]

        # --- 4. LÓGICA DE HORARIO MIXTA (FIJO vs POR HORAS) ---
        tareo_hoy = TareoDiario.objects.filter(trabajador=trabajador, fecha=hoy_fecha).first()

        tiene_horario = False
        es_por_horas = False  # <--- NUEVA BANDERA
        meta_horas = 0.0      # <--- NUEVO CAMPO
        horario_entrada = None
        horario_salida = None
        es_tardanza = False
        mensaje = "Sin horario"

        if tareo_hoy:
            # CASO 1: JORNADA POR HORAS (Tiene horas asignadas pero NO hora de entrada fija)
            if tareo_hoy.jornada_horas and tareo_hoy.jornada_horas > 0 and not tareo_hoy.hora_entrada:
                tiene_horario = True
                es_por_horas = True
                meta_horas = float(tareo_hoy.jornada_horas)
                
                # Mensaje dinámico según avance
                if tareo_hoy.horas_trabajadas_validas >= meta_horas:
                    mensaje = "Meta cumplida ✅"
                elif ultimo_tipo == 'Entrada':
                    mensaje = "Jornada en curso..."
                else:
                    mensaje = f"Debes cumplir {meta_horas} horas hoy"

            # CASO 2: HORARIO FIJO (Tiene hora de entrada definida)
            elif tareo_hoy.hora_entrada:
                tiene_horario = True
                es_por_horas = False
                horario_entrada = tareo_hoy.hora_entrada.strftime("%H:%M")
                horario_salida = tareo_hoy.hora_salida.strftime("%H:%M") if tareo_hoy.hora_salida else "--:--"

                # Lógica de tardanza estándar
                if tareo_hoy.hora_entrada_real:
                    if tareo_hoy.horas_tardanza >= TARDANZA_MINIMA_HORAS:
                        es_tardanza = True
                        mensaje = f"Tardanza ({tareo_hoy.horas_tardanza}h)"
                    else:
                        mensaje = "A tiempo"
                else:
                    entrada_dt = lima_tz.localize(datetime.combine(hoy_fecha, tareo_hoy.hora_entrada))
                    if ahora_lima > (entrada_dt + timedelta(minutes=TOLERANCIA_TARDANZA_MINUTOS)):
                        es_tardanza = True
                        mensaje = "Marcación tardía"
                    else:
                        mensaje = "A tiempo"

        return Response({
            'ultimoTipoMarcacion': ultimo_tipo,
            'ubicacionesPermitidas': ubicaciones_json,
            # DATOS NUEVOS
            'tiene_horario': tiene_horario,
            'es_por_horas': es_por_horas,   # True si es flexible
            'meta_horas': meta_horas,       # Ej: 3.5
            'horario_entrada': horario_entrada,
            'horario_salida': horario_salida,
            'es_tardanza': es_tardanza,
            'mensaje_aviso': mensaje
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Solo usuarios logeados pueden usar esto
def cambiar_contrasena(request):
    user = request.user
    password_actual = request.data.get('password_actual')
    nueva_password = request.data.get('nueva_password')

    # 1. Verificamos que sepa su contraseña actual por seguridad
    if not user.check_password(password_actual):
        return Response({"error": "La contraseña actual es incorrecta."}, status=400)
    
    # 2. Si todo está bien, la cambiamos
    user.set_password(nueva_password)
    user.save()
    
    return Response({"mensaje": "Contraseña actualizada exitosamente."}, status=200)


class RegistrarAsistenciaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        print(f"\n--- [API] Intento de marca: {request.user.username} ---")
        
        try:
            # 1. Validaciones Básicas (Dispositivo y Usuario)
            device_id = request.data.get('device_id')
            usuario_actual = request.user

            if not device_id:
                return Response({'detail': 'El ID del dispositivo es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                trabajador = Trabajador.objects.get(user=usuario_actual)
            except Trabajador.DoesNotExist:
                return Response({'detail': 'Usuario no vinculado a un trabajador activo.'}, status=status.HTTP_400_BAD_REQUEST)

            # =================================================================
            # FUNCIÓN AUXILIAR INTERNA: Para guardar el fraude fácilmente
            # =================================================================
            def registrar_fraude_bd(motivo):
                IntentoFraude.objects.create(
                    trabajador=trabajador,
                    motivo_detectado=motivo,
                    device_id=device_id,
                    # Buscamos la lat/lng en todas las posibles variables que envíe la app
                    latitud_reportada=request.data.get('latitud') or request.data.get('latitude') or request.data.get('lat'),
                    longitud_reportada=request.data.get('longitud') or request.data.get('longitude') or request.data.get('lng')
                )
                print(f"[ALERTA] Fraude guardado en BD: {motivo}")

            # Lógica de Dispositivo (Crear o validar)
            dispositivo, created = Dispositivo.objects.get_or_create(
                id=device_id,
                defaults={'nombre': f"Móvil de {trabajador.nombre_completo}"}
            )
            if created:
                dispositivo.trabajadores_permitidos.add(usuario_actual)

            if not dispositivo.trabajadores_permitidos.filter(pk=usuario_actual.pk).exists():
                registrar_fraude_bd('Dispositivo no autorizado para el trabajador')
                return Response({'detail': 'No tienes permiso para marcar en este dispositivo.'}, status=status.HTTP_403_FORBIDDEN)

            # =================================================================
            # BLOQUEO EXPLÍCITO DE LA APP (Fake GPS, Root, VPN)
            # =================================================================
            # Evaluamos si viene como booleano nativo o como string ('true', '1')
            is_fraud = request.data.get('is_fraud') in [True, 'true', 'True', 1, '1']
            fraudulent = request.data.get('fraudulent') in [True, 'true', 'True', 1, '1']
            bloqueo_app = is_fraud or fraudulent
            
            motivo_bloqueo_app = (
                request.data.get('securityReason')
                or request.data.get('motivoBloqueo')
                or request.data.get('blockedReason')
                or request.data.get('reason')
                or 'Intento bloqueado por validacion de seguridad del celular'
            )
            
            if bloqueo_app:
                registrar_fraude_bd(str(motivo_bloqueo_app))
                return Response({'detail': str(motivo_bloqueo_app)}, status=status.HTTP_403_FORBIDDEN)
            
            # =================================================================
            # --- 2. CANDADO DE SEGURIDAD: VALIDAR ASIGNACIÓN DE TURNO ---
            # =================================================================
            # localdate() usa America/Lima; con now().date() (UTC en el servidor)
            # a partir de las 19:00 de Lima se buscaba el tareo del día siguiente
            # y se bloqueaban las marcaciones de la tarde/noche.
            hoy = timezone.localdate()
            
            try:
                # Buscamos el tareo asignado para hoy
                tareo_hoy = TareoDiario.objects.get(trabajador=trabajador, fecha=hoy)
                
                # Restricción 1: Si es Día Libre ('D')
                if tareo_hoy.estado == 'D':
                    registrar_fraude_bd('Intento de marcacion en dia libre')
                    return Response({
                        'detail': 'Hoy está registrado como tu Día Libre. No se permite marcar.'
                    }, status=status.HTTP_403_FORBIDDEN)
                    
            except TareoDiario.DoesNotExist:
                # Restricción 2: No existe turno asignado en la web
                registrar_fraude_bd('Intento de marcacion sin turno programado')
                return Response({
                    'detail': 'No tienes un turno programado para hoy. Por favor contacta a tu supervisor.'
                }, status=status.HTTP_403_FORBIDDEN)
            # =================================================================

            # 3. Guardar la Asistencia (Solo si pasó todas las validaciones y no hubo fraude)
            serializer = AsistenciaSerializer(data=request.data)
            if serializer.is_valid():
                # ---> AQUÍ AGREGAMOS EL CAMPO ORIGEN <---
                serializer.save(
                    usuario=usuario_actual,
                    origen='APP'  # Le decimos explícitamente que viene de la aplicación
                )
                
                # 4. CÁLCULO AUTOMÁTICO
                advertencia = None
                try:
                    recalcular_asistencia_diaria(tareo_hoy)
                    print(f"✅ Asistencia registrada y procesada para {trabajador}")

                    tareo_hoy.refresh_from_db()
                    if tareo_hoy.etiqueta_estado in ('FUERA_HORARIO', 'TARDANZA'):
                        advertencia = {
                            'tipo': tareo_hoy.etiqueta_estado,
                            'mensaje': (
                                f'Tu marcación fue clasificada como '
                                f'{tareo_hoy.get_etiqueta_estado_display()}.'
                            ),
                            'detalle': tareo_hoy.detalle_marca or '',
                        }
                except Exception as e:
                    print(f"⚠️ Error en el cálculo matemático: {e}")

                response_data = dict(serializer.data)
                if advertencia:
                    response_data['advertencia'] = advertencia
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            print(f"[API] ERROR CRÍTICO:")
            traceback.print_exc()
            return Response({'detail': 'Error interno del servidor.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ListarFaltasView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FaltaPendienteSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            trabajador = Trabajador.objects.get(user=user)
            hoy = timezone.localdate()
            # --- CAMBIO IMPORTANTE ---
            # Ya NO llamamos a 'asegurar_faltas_existentes'.
            # Solo buscamos registros que EXISTAN y tengan resultado='F'.
            
            return TareoDiario.objects.filter(
                trabajador=trabajador, 
                resultado='F', # El registro existe (creado por RRHH) y es Falta
                justificacion__isnull=True,
                fecha__lt=hoy
            ).order_by('-fecha')

        except Trabajador.DoesNotExist:
            return TareoDiario.objects.none()


class CrearJustificacionView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CrearJustificacionSerializer
    # AGREGAMOS JSONParser para que acepte los datos que envía Flutter
    parser_classes = (JSONParser, MultiPartParser, FormParser) 

    def create(self, request, *args, **kwargs):
        print("🔍 INTENTO DE JUSTIFICACIÓN DESDE FLUTTER")
        
        # 1. Obtenemos los datos (mutable para poder inyectar el ID del tareo)
        data = request.data.copy()
        
        # 2. Lógica para convertir "FECHA" (que envía Flutter) a "TAREO ID" (que pide Django)
        if 'fecha' in data:
            fecha_str = data['fecha'] # Flutter envía "2026-01-13"
            usuario = request.user
            
            try:
                trabajador = Trabajador.objects.get(user=usuario)
                # Buscamos el tareo de esa fecha
                tareo = TareoDiario.objects.get(trabajador=trabajador, fecha=fecha_str)
                
                # Inyectamos el ID del tareo en los datos para el Serializer
                data['tareo'] = tareo.id 
                
            except Trabajador.DoesNotExist:
                 return Response({"detail": "Usuario no es trabajador"}, status=status.HTTP_400_BAD_REQUEST)
            except TareoDiario.DoesNotExist:
                 return Response({"detail": f"No se encontró asistencia para la fecha {fecha_str}"}, status=status.HTTP_404_NOT_FOUND)

        # 3. Validación Estándar del Serializer
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            print("❌ Error de validación:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListarMisSolicitudesHEView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SolicitudHorasExtraSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            trabajador = Trabajador.objects.get(user=user)
            # Retornamos todas las solicitudes ordenadas por fecha reciente
            return SolicitudHorasExtra.objects.filter(
                trabajador=trabajador
            ).order_by('-fecha_horas_extra')
        except Trabajador.DoesNotExist:
            return SolicitudHorasExtra.objects.none()


class HistorialAsistenciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve el historial del mes actual (o el solicitado) para pintar el calendario
        """
        try:
            trabajador = Trabajador.objects.get(user=request.user)
        except Trabajador.DoesNotExist:
            return Response({"error": "Usuario no es trabajador"}, status=400)

        # Filtramos por mes (puedes recibir ?mes=11&anio=2024 en el futuro)
        hoy = timezone.localtime()
        mes = int(request.query_params.get('mes', hoy.month))
        anio = int(request.query_params.get('anio', hoy.year))

        tareos = TareoDiario.objects.filter(
            trabajador=trabajador,
            fecha__year=anio,
            fecha__month=mes
        ).select_related('justificacion') # Optimizamos consulta

        data = []
        for t in tareos:
            # Estado de justificación (si existe)
            just_estado = None
            if hasattr(t, 'justificacion'):
                just_estado = t.justificacion.estado_solicitud # PENDIENTE, APROBADO...

            item = {
                "fecha": t.fecha.strftime('%Y-%m-%d'),
                "resultado": t.resultado, # 'A' (Asistió), 'F' (Falta)
                "estado_planificado": t.estado, # C, O, P, J
                
                # Horarios para comparar
                "entrada_prog": t.hora_entrada.strftime('%H:%M') if t.hora_entrada else "--:--",
                "salida_prog": t.hora_salida.strftime('%H:%M') if t.hora_salida else "--:--",
                
                "entrada_real": t.hora_entrada_real.strftime('%H:%M') if t.hora_entrada_real else None,
                "salida_real": t.hora_salida_real.strftime('%H:%M') if t.hora_salida_real else None,
                
                "tardanza_horas": t.horas_tardanza if t.horas_tardanza >= TARDANZA_MINIMA_HORAS else Decimal('0.00'),
                "justificacion_estado": just_estado 
            }
            data.append(item)

        return Response(data)


class ListarMarcacionesLogView(APIView):
    """
    Devuelve las últimas 30 marcaciones (entradas/salidas) para el historial en la App.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Obtenemos las últimas 30
        marcaciones = Asistencia.objects.filter(usuario=user).order_by('-timestamp')[:30]
        
        data = []
        for m in marcaciones:
            # Convertimos a hora local para mostrar correctamente
            fecha_local = timezone.localtime(m.timestamp)
            data.append({
                'tipo': m.tipo_marcacion,
                'fecha_hora': fecha_local.strftime("%Y-%m-%d %H:%M:%S"),
                'ubicacion': m.nombre_ubicacion,
                'sincronizado': True # Si viene del server, ya está sincronizado
            })
            
        return Response(data)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_nombre(request):
    user = request.user
    
    # Extraemos los datos enviados desde Flutter
    nombres = request.data.get('nombres', '').strip()
    ap_paterno = request.data.get('apellido_paterno', '').strip()
    ap_materno = request.data.get('apellido_materno', '').strip()

    # Validamos que no envíen campos vacíos
    if not nombres or not ap_paterno or not ap_materno:
        return Response({"error": "Todos los campos (nombres y apellidos) son obligatorios."}, status=400)

    try:
        # Buscamos al trabajador vinculado a esta sesión
        trabajador = Trabajador.objects.get(user=user)
        
        # Actualizamos sus datos
        trabajador.nombres = nombres
        trabajador.apellido_paterno = ap_paterno
        trabajador.apellido_materno = ap_materno
        trabajador.save()

        # Opcional: Actualizamos también el modelo User base de Django por orden
        user.first_name = nombres
        user.last_name = f"{ap_paterno} {ap_materno}".strip()
        user.save()

        return Response({
            "mensaje": "Nombre actualizado exitosamente.",
            "nuevo_nombre_completo": trabajador.nombre_completo
        }, status=200)

    except Trabajador.DoesNotExist:
        return Response({"error": "No se encontró un perfil de trabajador para este usuario."}, status=404)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_email(request):
    user = request.user
    nuevo_email = request.data.get('email', '').strip()

    if not nuevo_email:
        return Response({"error": "El correo es obligatorio."}, status=400)

    try:
        trabajador = Trabajador.objects.get(user=user)
        trabajador.email = nuevo_email
        trabajador.save()
        
        # Opcional: Actualizar el email del modelo User base de Django
        user.email = nuevo_email
        user.save()

        return Response({"mensaje": "Correo actualizado.", "nuevo_email": nuevo_email}, status=200)
    except Trabajador.DoesNotExist:
        return Response({"error": "No se encontró el trabajador."}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_telefono(request):
    user = request.user
    nuevo_telefono = request.data.get('telefono', '').strip()

    if not nuevo_telefono:
        return Response({"error": "El teléfono es obligatorio."}, status=400)

    try:
        trabajador = Trabajador.objects.get(user=user)
        trabajador.telefono = nuevo_telefono
        trabajador.save()

        return Response({"mensaje": "Teléfono actualizado.", "nuevo_telefono": nuevo_telefono}, status=200)
    except Trabajador.DoesNotExist:
        return Response({"error": "No se encontró el trabajador."}, status=404)


# ==============================================================================
# CAV-182: Sincronizacion incremental de usuarios autorizados
# ==============================================================================
def _calcular_checksum_usuarios(usuarios_data):
    """
    Genera un checksum estable (SHA-256) sobre la lista de usuarios ya
    serializada, ordenada por DNI para que el resultado sea determinista
    sin importar el orden en que la base de datos devuelva las filas.
    El cliente movil recalcula este mismo checksum para verificar que
    la lista no fue alterada/corrompida en el camino (CAV-183).

    IMPORTANTE: NO se usa sort_keys=True aqui. El checksum debe calcularse
    sobre la MISMA representacion JSON que efectivamente se envia en la
    respuesta (orden de claves tal como se construyen los dicts), porque
    el cliente recalcula el checksum a partir de lo que recibio por HTTP,
    no de una version re-ordenada que nunca viaja por la red.
    """
    normalizados = sorted(usuarios_data, key=lambda u: u['dni'])
    canonical = json.dumps(normalizados, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class UsuariosAutorizadosSyncView(APIView):
    """
    CAV-182: Endpoint de sincronizacion incremental de usuarios autorizados.

    GET /api/usuarios-autorizados/sync/?since=<ISO-8601, opcional>

    - Sin 'since': devuelve TODOS los trabajadores con cuenta de usuario
      vinculada (sync completo, primera vez que el dispositivo sincroniza).
    - Con 'since': devuelve solo los que cambiaron (activo, datos, etc.)
      despues de esa fecha/hora (sync incremental).

    Respuesta:
    {
        "version": "<ISO-8601, usar como 'since' en la proxima llamada>",
        "checksum": "<sha256 de la lista 'usuarios' tal como se envia>",
        "usuarios": [
            {"dni": ..., "username": ..., "nombre_completo": ...,
             "activo": ..., "actualizado_en": ...},
            ...
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since_raw = request.query_params.get('since')
        queryset = Trabajador.objects.filter(user__isnull=False).select_related('user')

        if since_raw:
            since_dt = parse_datetime(since_raw)
            if since_dt is None:
                return Response(
                    {"error": "Parametro 'since' invalido. Debe ser una fecha ISO-8601."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.is_naive(since_dt):
                since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())
            queryset = queryset.filter(actualizado_en__gt=since_dt)

        queryset = queryset.order_by('dni')

        usuarios_data = [
            {
                'dni': t.dni,
                'username': t.user.username,
                'nombre_completo': t.nombre_completo,
                'activo': t.activo,
                'actualizado_en': t.actualizado_en.isoformat(),
            }
            for t in queryset
        ]

        # Validamos con el serializer para garantizar el contrato de datos
        serializer = UsuarioAutorizadoSerializer(data=usuarios_data, many=True)
        serializer.is_valid(raise_exception=True)

        checksum = _calcular_checksum_usuarios(usuarios_data)

        return Response({
            'version': timezone.now().isoformat(),
            'checksum': checksum,
            'usuarios': usuarios_data,
        }, status=status.HTTP_200_OK)