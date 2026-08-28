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

from django.conf import settings as django_settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import IntegrityError
from django.db.models import Max, Q
from django.contrib.auth.decorators import login_required

# Importaciones de modelos
from recursoshumanos.models import (
    SolicitudHorasExtra, Trabajador, Dispositivo, Asistencia,
    Justificacion, TareoDiario, IntentoFraude, EventoLoginOffline
)
from administracion.services.feriados import obtener_feriado

# Importaciones de serializers
from .serializers import (
    MyTokenObtainPairSerializer, AsistenciaSerializer,
    FaltaPendienteSerializer, CrearJustificacionSerializer,
    SolicitudHorasExtraSerializer, UsuarioAutorizadoSerializer,
    EventoLoginOfflineSerializer
)

# Importaciones de servicios
from recursoshumanos.services import recalcular_asistencia_diaria
from admin_panel.settings import db

# Constantes
TARDANZA_MINIMA_HORAS = Decimal('0.25')
TOLERANCIA_TARDANZA_MINUTOS = 3

# Tope absoluto de antiguedad para una marca sincronizada. NO es una caducidad
# de sincronizacion: en faena minera un trabajador puede pasar meses o anios sin
# senal y su cola sigue siendo valida al volver, asi que el valor por defecto se
# mide en anios y solo existe como red de seguridad contra un reloj corrupto.
ASISTENCIA_ANTIGUEDAD_MAXIMA_DIAS = getattr(
    django_settings, 'ASISTENCIA_ANTIGUEDAD_MAXIMA_DIAS', 3650
)

# Margen de tolerancia para relojes adelantados antes de considerar futura una
# marca. Tras meses sin sincronizar NTP la deriva del reloj es esperable.
ASISTENCIA_MARGEN_RELOJ_FUTURO_MINUTOS = getattr(
    django_settings, 'ASISTENCIA_MARGEN_RELOJ_FUTURO_MINUTOS', 15
)


def _fecha_negocio_de_marca(raw_timestamp):
    """Deriva la fecha de negocio (America/Lima) del timestamp que envia el movil.

    Es la correccion central de este fix: una marca pertenece al dia en que se
    hizo, no al dia en que el worker offline logro subirla. Devuelve la tupla
    ``(fecha, datetime_aware)``; si el payload no trae timestamp o es ilegible
    cae a ``localdate()``, que es el comportamiento correcto para una marca en
    tiempo real.

    Usa ``localtime()`` y NUNCA ``.date()`` sobre el datetime crudo: el servidor
    corre en UTC y a partir de las 19:00 de Lima ``.date()`` devuelve el dia
    siguiente. Ese bug ya se corrigio una vez en este archivo (ver el candado de
    turno mas abajo); no reintroducirlo.

    Contrato de zona horaria, del que depende el fix de MARCA_FUTURA:

      * Si el payload trae offset explicito (``...Z`` o ``...-05:00``), se
        respeta tal cual. Es lo que manda la app desde el fix de zona horaria.
      * Si viene sin zona, se asume America/Lima. Es lo que manda el parque
        movil viejo, y hay que seguir soportandolo mientras exista.

    Las dos formas conviven a proposito: asi este cambio se puede desplegar
    antes que la app, sin coordinar una ventana. Un celular con la zona horaria
    mal configurada mandaba hora local de OTRA zona sin decirlo, se leia como
    hora de Lima y caia como marca futura; con offset explicito eso ya no pasa.
    """
    if not raw_timestamp:
        return timezone.localdate(), None

    if isinstance(raw_timestamp, datetime):
        dt = raw_timestamp
    else:
        try:
            dt = parse_datetime(str(raw_timestamp))
        except (TypeError, ValueError):
            dt = None

    if dt is None:
        return timezone.localdate(), None

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)

    return timezone.localtime(dt).date(), dt
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
            print(f"[WARN] No se pudo registrar intento de fraude en SQL: {sql_exc}")

        # 2) Guardado en Firestore (si está disponible).
        try:
            db.collection('asistencias_fraudulentas').add(payload)
        except Exception as fs_exc:
            print(f"[WARN] No se pudo registrar intento de fraude en Firestore: {fs_exc}")
    except Exception as log_exc:
        print(f"[WARN] No se pudo registrar intento de fraude: {log_exc}")


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
        print("[ALERTA] DEBUG: INICIO DE SOLICITUD DE HORAS EXTRA")
        print(f"[USER] Usuario autenticado: {request.user.username}")
        
        # 1. Ver qué datos llegaron realmente desde Flutter
        print(f"[DATA] Datos recibidos (request.data): {json.dumps(request.data, indent=2)}")

        serializer = self.get_serializer(data=request.data)
        
        # 2. Validar y si falla, IMPRIMIR EL ERROR
        if not serializer.is_valid():
            print("[ERROR] ERROR DE VALIDACIÓN:")
            print(json.dumps(serializer.errors, indent=2)) # Esto nos dirá EXACTAMENTE qué campo falla
            print("="*50 + "\n")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Intentar guardar (ejecuta perform_create)
        try:
            self.perform_create(serializer)
        except Exception as e:
            print(f"[ERROR] ERROR AL GUARDAR (perform_create): {str(e)}")
            print("="*50 + "\n")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Éxito
        headers = self.get_success_headers(serializer.data)
        print("[OK] SOLICITUD CREADA CON ÉXITO")
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

        # Feriado del día para ESTE trabajador (scope nacional/regional/empresa,
        # CAV-13). El móvil usa esto para el banner "Día Feriado" (CAV-64).
        feriado_hoy = obtener_feriado(hoy_fecha, sede=trabajador.sede, empresa=trabajador.empresa)

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
                    mensaje = "Meta cumplida [OK]"
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
            'mensaje_aviso': mensaje,
            # Feriado (CAV-13/CAV-64): el móvil muestra el banner con estos campos.
            'es_feriado': feriado_hoy is not None,
            'nombre_feriado': feriado_hoy.nombre if feriado_hoy else None,
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
            # --- 2. IDEMPOTENCIA: ¿ya registramos esta misma marca? ---
            # =================================================================
            # El worker offline reintenta cuando pierde la respuesta, cosa que
            # sobre una conexión de faena es la norma y no la excepción. El
            # `client_uuid` lo genera el móvil al ENCOLAR la marca y lo persiste
            # localmente, así que sobrevive a los reintentos e identifica la
            # misma marcación aunque el POST llegue tres veces.
            #
            # Va ANTES de cualquier validación a propósito: un reintento no debe
            # volver a validar turno, ni recalcular el tareo, ni poder producir
            # un 403 sobre una marca que en el primer intento ya se guardó bien.
            # Se acepta camelCase además de snake_case para que un desajuste de
            # nomenclatura con el móvil no repita el bug de ignorarlo en silencio.
            client_uuid = request.data.get('client_uuid') or request.data.get('clientUuid')
            if client_uuid:
                marca_existente = Asistencia.objects.filter(client_uuid=client_uuid).first()
                if marca_existente:
                    print(f"[API] Reintento idempotente de {client_uuid}: se devuelve la marca #{marca_existente.pk}")
                    return Response(
                        AsistenciaSerializer(marca_existente).data,
                        status=status.HTTP_200_OK
                    )

            # =================================================================
            # --- 3. FECHA DE NEGOCIO: el día de la MARCA, no el de la subida ---
            # =================================================================
            # localdate() usa America/Lima; con now().date() (UTC en el servidor)
            # a partir de las 19:00 de Lima se buscaba el tareo del día siguiente
            # y se bloqueaban las marcaciones de la tarde/noche.
            hoy = timezone.localdate()

            # Antes toda la validación colgaba de `hoy`, o sea del día en que
            # LLEGABA la petición. Una marca hecha offline el lunes y subida el
            # miércoles se validaba contra el turno del miércoles: si ese día era
            # libre o no tenía turno, respondía 403 y el dato de planilla del
            # lunes se perdía para siempre, además de registrar un fraude falso.
            fecha_negocio, timestamp_marca = _fecha_negocio_de_marca(request.data.get('timestamp'))

            if timestamp_marca is not None:
                # Al derivar la fecha del payload, el reloj del celular pasa a
                # determinar planilla. Tras meses sin NTP puede haber derivado, o
                # haber sido movido a mano. Un timestamp futuro no puede ser una
                # marca real; aun así NO se registra IntentoFraude, porque la
                # deriva de reloj no es prueba de manipulación y grabar fraude
                # ahí repetiría justo el error que este fix viene a corregir.
                margen_reloj = timedelta(minutes=ASISTENCIA_MARGEN_RELOJ_FUTURO_MINUTOS)
                if timestamp_marca > timezone.now() + margen_reloj:
                    return Response({
                        'codigo': 'MARCA_FUTURA',
                        'detail': 'La marcación tiene fecha futura. Revisa la hora de tu dispositivo.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Red de seguridad, no caducidad: el tope se mide en años (ver la
                # constante). Una marca de hace 14 meses entra sin problema.
                if (hoy - fecha_negocio).days > ASISTENCIA_ANTIGUEDAD_MAXIMA_DIAS:
                    return Response({
                        'codigo': 'MARCA_EXPIRADA',
                        'detail': (
                            'La marcación es demasiado antigua para registrarse '
                            'automáticamente. Contacta a Recursos Humanos.'
                        ),
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Si el día de la marca ya pasó, viene de la cola offline. Eso es
            # desfase de sincronización, no fraude, y se trata distinto.
            es_marca_atrasada = fecha_negocio < hoy

            # =================================================================
            # --- 4. CANDADO DE SEGURIDAD: VALIDAR ASIGNACIÓN DE TURNO ---
            # =================================================================
            if es_marca_atrasada:
                # Tras meses en faena el tareo de ese día puede no existir: RRHH
                # nunca cargó el turno, el trabajador se incorporó después, o el
                # tareo se archivó. Antes eso caía en DoesNotExist -> 403 y la
                # marca se perdía igual, sólo que por otra razón.
                #
                # Lo creamos al vuelo, que es exactamente lo que ya hace la
                # importación biométrica ante el mismo problema (ver
                # recursoshumanos/servicios_asistencias.py). El estado 'O' es
                # explícito y obligatorio: sin él el tareo podría nacer con un
                # estado que lo haga caer en la validación de día libre y volver
                # a dar 403. Un tareo así no tiene horario, y el motor de reglas
                # lo clasifica ASISTIÓ + SIN_HORARIO sin tardanza, dejándolo
                # visible para que RRHH lo concilie.
                tareo, _ = TareoDiario.objects.get_or_create(
                    trabajador=trabajador,
                    fecha=fecha_negocio,
                    defaults={'estado': 'O', 'resultado': 'F'},
                )
                # Deliberadamente NO se corta por estado 'D': el motor de reglas
                # ya acepta marcas en día libre (ASISTIÓ + etiqueta DIA_LIBRE,
                # sin evaluar tardanza), así que rechazarlas aquí contradiría una
                # regla que el dominio ya tiene escrita y perdería planilla.
                # Tampoco se registra IntentoFraude en esta rama.
            else:
                # Marca en tiempo real: el control antifraude queda INTACTO.
                # Intentar marcar HOY en tu día libre o sin turno asignado sigue
                # siendo sospechoso y se sigue registrando como tal.
                try:
                    # Buscamos el tareo asignado para hoy.
                    #
                    # OJO: si el tareo ya existe, el permiso de marcar sin
                    # horario NO se vuelve a consultar. Es deliberado. Una vez
                    # que una marca autorizada creo el tareo del dia, ese dia
                    # queda abierto aunque RRHH revoque el permiso: cortar en
                    # seco dejaria una Entrada sin Salida, con el dia a medio
                    # cerrar para planilla y sin nada que el trabajador pueda
                    # hacer. La revocacion aplica desde el dia siguiente, que es
                    # cuando vuelve a no haber tareo. Ver
                    # RevocacionPermisoMarcaSinHorarioTests.
                    tareo = TareoDiario.objects.get(trabajador=trabajador, fecha=fecha_negocio)

                    # Restricción 1: Si es Día Libre ('D')
                    if tareo.estado == 'D':
                        registrar_fraude_bd('Intento de marcacion en dia libre')
                        return Response({
                            'detail': 'Hoy está registrado como tu Día Libre. No se permite marcar.'
                        }, status=status.HTTP_403_FORBIDDEN)

                except TareoDiario.DoesNotExist:
                    # Restricción 2: No existe turno asignado en la web.
                    #
                    # Única excepción: RRHH habilitó explícitamente a ESTE
                    # trabajador a marcar sin horario. El permiso se evalúa
                    # contra `fecha_negocio` y no contra hoy, porque una marca
                    # offline sincronizada el mismo día también cae acá y lo que
                    # importa es si el permiso regía cuando marcó.
                    if trabajador.puede_marcar_sin_horario_en(fecha_negocio):
                        # Mismo tratamiento que la rama de marca atrasada: el
                        # tareo se crea al vuelo con estado 'O' (sin horario),
                        # que el motor de reglas clasifica ASISTIÓ + SIN_HORARIO
                        # sin fabricar tardanza. No es fraude, no se registra.
                        tareo, _ = TareoDiario.objects.get_or_create(
                            trabajador=trabajador,
                            fecha=fecha_negocio,
                            defaults={'estado': 'O', 'resultado': 'F'},
                        )
                    else:
                        registrar_fraude_bd('Intento de marcacion sin turno programado')
                        return Response({
                            'detail': 'No tienes un turno programado para hoy. Por favor contacta a tu supervisor.'
                        }, status=status.HTTP_403_FORBIDDEN)
            # =================================================================

            # 5. Guardar la Asistencia (Solo si pasó todas las validaciones y no hubo fraude)
            # Se normaliza el client_uuid al nombre del modelo para que también
            # se persista cuando el móvil lo manda en camelCase.
            datos_marca = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            if client_uuid:
                datos_marca['client_uuid'] = client_uuid

            serializer = AsistenciaSerializer(data=datos_marca)
            if serializer.is_valid():
                # ---> AQUÍ AGREGAMOS EL CAMPO ORIGEN <---
                try:
                    serializer.save(
                        usuario=usuario_actual,
                        origen='APP'  # Le decimos explícitamente que viene de la aplicación
                    )
                except IntegrityError:
                    # Dos reintentos simultáneos del worker pueden pasar ambos el
                    # filtro de arriba y chocar recién contra el unique de la BD,
                    # que es la garantía real de idempotencia. Traducimos ese
                    # choque a la misma respuesta que el reintento secuencial.
                    marca_existente = (
                        Asistencia.objects.filter(client_uuid=client_uuid).first()
                        if client_uuid else None
                    )
                    if marca_existente:
                        return Response(
                            AsistenciaSerializer(marca_existente).data,
                            status=status.HTTP_200_OK
                        )
                    raise

                # 6. CÁLCULO AUTOMÁTICO (sobre el tareo del día de la MARCA)
                advertencia = None
                try:
                    recalcular_asistencia_diaria(tareo)
                    print(f"[OK] Asistencia registrada y procesada para {trabajador}")

                    tareo.refresh_from_db()
                    if tareo.etiqueta_estado in ('FUERA_HORARIO', 'TARDANZA'):
                        advertencia = {
                            'tipo': tareo.etiqueta_estado,
                            'mensaje': (
                                f'Tu marcación fue clasificada como '
                                f'{tareo.get_etiqueta_estado_display()}.'
                            ),
                            'detalle': tareo.detalle_marca or '',
                        }
                except Exception as e:
                    print(f"[WARN] Error en el cálculo matemático: {e}")

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
        print("[DEBUG] INTENTO DE JUSTIFICACIÓN DESDE FLUTTER")
        
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
            print("[ERROR] Error de validación:", serializer.errors)
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

    Por la misma razon va ensure_ascii=False: DRF renderiza con
    UNICODE_JSON=True, o sea que manda los acentos como UTF-8 literal
    ("Jose Martinez" con tilde viaja como bytes \\xc3\\xad). El default de
    json.dumps los escaparia a "\\u00ed" y el checksum dejaria de
    corresponder a lo que realmente sale por la red. El cliente Dart usa
    jsonEncode, que tampoco escapa, asi que sin esto ningun dataset con
    tildes o enies coincide nunca.
    """
    normalizados = sorted(usuarios_data, key=lambda u: u['dni'])
    canonical = json.dumps(normalizados, separators=(',', ':'), ensure_ascii=False)
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
        base = Trabajador.objects.filter(user__isnull=False)
        queryset = base.select_related('user')

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

        # El cursor sale de los DATOS, no del reloj del servidor.
        #
        # Antes era `timezone.now()` evaluado junto al `Response`, o sea
        # DESPUES de leer. Eso abria un hueco: todo lo que cambiara entre la
        # lectura y ese instante quedaba por debajo del cursor que el cliente
        # se llevaba, y el proximo incremental (`actualizado_en > since`) ya no
        # lo alcanzaba. No se recuperaba solo -el cursor ya habia avanzado-,
        # asi que el cambio se perdia para siempre y en silencio: un trabajador
        # dado de baja seguia entrando al login offline meses despues.
        #
        # La marca de agua de la tabla no puede dejar hueco por construccion:
        # cualquier fila guardada despues de esta lectura tiene un
        # `actualizado_en` estrictamente mayor, asi que el proximo incremental
        # la trae. Ademas deja de depender del reloj, que entre varios workers
        # puede tener deriva, y de su resolucion.
        #
        # Se calcula sobre `base` (todas las filas) y no sobre `queryset`, que
        # en una llamada incremental ya viene filtrado: si no hubo cambios, el
        # maximo de ese conjunto vacio seria nulo y el cursor saltaria al
        # reloj, reintroduciendo el mismo hueco.
        #
        # `timezone.now()` queda solo de respaldo para la tabla vacia, donde no
        # hay marca de agua posible y tampoco hay nada que perder.
        version = base.aggregate(Max('actualizado_en'))['actualizado_en__max']

        return Response({
            'version': (version or timezone.now()).isoformat(),
            'checksum': checksum,
            'usuarios': usuarios_data,
        }, status=status.HTTP_200_OK)


# ==============================================================================
# CAV-83: Reporte de eventos de login offline (auditoria)
# ==============================================================================
class RegistrarEventoLoginOfflineView(APIView):
    """
    CAV-83: recibe el reporte de que el usuario autenticado inicio sesion
    en modo offline (validado localmente contra el hash cifrado, CAV-81),
    una vez que el dispositivo recupera conexion.

    Es puramente informativo/de auditoria: no crea ninguna sesion nueva
    ni emite tokens. Para llegar aqui el dispositivo ya debe tener un
    JWT valido (el mismo de su ultimo login online), asi que
    'request.user' identifica de forma segura a quien reporta el evento.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EventoLoginOfflineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trabajador = Trabajador.objects.get(user=request.user)
        except Trabajador.DoesNotExist:
            return Response(
                {"error": "No se encontró el trabajador asociado a este usuario."},
                status=status.HTTP_404_NOT_FOUND,
            )

        evento = EventoLoginOffline.objects.create(
            trabajador=trabajador,
            device_id=serializer.validated_data['device_id'],
            fecha_hora_offline=serializer.validated_data['fecha_hora_offline'],
        )

        return Response(
            {"mensaje": "Evento de login offline registrado.", "id": evento.id},
            status=status.HTTP_201_CREATED,
        )