from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from recursoshumanos.models import (
    SolicitudHorasExtra,
    Trabajador,
    Dispositivo,
    Asistencia,
    Justificacion,
    TareoDiario,
    ConfiguracionTolerancia,
    ToleranciaAuditoria,
)


class SolicitudHorasExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudHorasExtra
        fields = [
            'id',
            'trabajador',
            'fecha_horas_extra',
            'cantidad_horas',
            'justificacion',
            'estado',
            'creado_en',
        ]
        read_only_fields = [
            'id',
            'trabajador',
            'estado',
            'creado_en',
        ]


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    device_id = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        data = super().validate(attrs)

        device_id = attrs.get('device_id')
        usuario_actual = self.user

        if not device_id:
            raise serializers.ValidationError({"detail": "El ID del dispositivo es obligatorio."})

        # --- Variables por defecto ---
        nombre_trabajador = usuario_actual.username
        area = "Sin Área"
        dni_trabajador = "No registrado"
        email_trabajador = "No registrado"
        telefono_trabajador = "No registrado"

        # --- Extracción de datos del Trabajador ---
        try:
            trabajador = Trabajador.objects.get(user=usuario_actual)
            nombre_trabajador = trabajador.nombre_completo
            dni_trabajador = trabajador.dni
            email_trabajador = trabajador.email if trabajador.email else 'No registrado'
            telefono_trabajador = trabajador.telefono if trabajador.telefono else 'No registrado'

            if trabajador.area and hasattr(trabajador.area, 'nombre'):
                area = trabajador.area.nombre

        except Trabajador.DoesNotExist:
            nombre_trabajador = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

        # ==========================================================
        # 🔒 CANDADO DE SEGURIDAD ESTRICTO (1 TRABAJADOR = 1 CELULAR) 🔒
        # ==========================================================
        
        # Buscamos si este usuario ya tiene algún dispositivo vinculado en la base de datos
        dispositivos_vinculados = Dispositivo.objects.filter(trabajadores_permitidos=usuario_actual)

        if dispositivos_vinculados.exists():
            # EL USUARIO YA TIENE UN CELULAR REGISTRADO
            # Verificamos si el device_id que intenta usar es exactamente el que ya tiene guardado
            if not dispositivos_vinculados.filter(id=device_id).exists():
                # ❌ ALERTA: Es un celular nuevo o la app fue reinstalada. ¡Bloqueamos el paso!
                raise serializers.ValidationError(
                    {"detail": "Ya tienes un dispositivo registrado. Si cambiaste de celular o reinstalaste la app, solicita a Recursos Humanos que libere tu equipo anterior."}
                )
            # ✅ Si llega aquí, es porque el device_id sí coincide. Todo en orden, lo dejamos pasar.
        else:
            # ES LA PRIMERA VEZ QUE INICIA SESIÓN (No tiene dispositivos vinculados)
            # Creamos o recuperamos el dispositivo en la BD y lo vinculamos a este usuario
            dispositivo, created = Dispositivo.objects.get_or_create(
                id=device_id,
                defaults={'nombre': f"Dispositivo de {nombre_trabajador}"}
            )
            dispositivo.trabajadores_permitidos.add(usuario_actual)

        # --- RESPUESTA FINAL AL CELULAR ---
        data.update({
            'user': {
                'nombre': nombre_trabajador,
                'usuario': usuario_actual.username,
                'dni': dni_trabajador,
                'area': area,
                'email': email_trabajador,
                'telefono': telefono_trabajador,
            }
        })

        return data

class AsistenciaSerializer(serializers.ModelSerializer):
    # `client_uuid` es unique=True en el modelo, asi que DRF le agregaria un
    # UniqueValidator por defecto y el reintento del worker offline moriria con
    # un 400 ANTES de que la vista pueda responder con la marca ya registrada.
    # Lo declaramos sin validadores: la unicidad la sigue garantizando la BD
    # (mas el except IntegrityError de la vista), y el duplicado se traduce a
    # una respuesta idempotente en vez de a un error.
    client_uuid = serializers.UUIDField(required=False, allow_null=True, validators=[])

    # Resultado de la geocerca evaluada EN EL SERVIDOR. Son read_only a
    # proposito: si el movil pudiera mandarlos, la validacion volveria a
    # depender del cliente, que es exactamente el agujero que esto cierra.
    zona_validada = serializers.CharField(
        source='ubicacion_validada.nombre', read_only=True, default=None
    )

    class Meta:
        model = Asistencia
        fields = [
            'id',
            'timestamp',
            'tipo_marcacion',
            'latitud',
            'longitud',
            'nombre_ubicacion',
            'device_id',
            'client_uuid',
            # Fecha de recepcion en servidor. Viaja solo para que RRHH pueda
            # auditar el desfase contra `timestamp` en las marcas atrasadas.
            'creado_en',
            'estado_geocerca',
            'zona_validada',
            'distancia_geocerca_m',
        ]
        read_only_fields = [
            'id',
            'creado_en',
            'estado_geocerca',
            'zona_validada',
            'distancia_geocerca_m',
        ]


class FaltaPendienteSerializer(serializers.ModelSerializer):
    fecha = serializers.DateField(format="%d/%m/%Y")
    dia_semana = serializers.SerializerMethodField()

    class Meta:
        model = TareoDiario
        fields = ['id', 'fecha', 'dia_semana']

    def get_dia_semana(self, obj):
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        return dias[obj.fecha.weekday()]


class CrearJustificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Justificacion
        fields = ['tareo', 'motivo', 'descripcion', 'archivo_evidencia']


class ToleranciaAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    tipo_horario_display = serializers.CharField(source='get_tipo_horario_display', read_only=True)

    class Meta:
        model = ToleranciaAuditoria
        fields = [
            'id', 'sede_nombre', 'tipo_horario', 'tipo_horario_display',
            'minutos_anteriores', 'minutos_nuevos', 'usuario_nombre', 'creado_en',
        ]
        read_only_fields = fields

    def get_usuario_nombre(self, obj):
        return obj.usuario.username if obj.usuario else 'Sistema'


class UsuarioAutorizadoSerializer(serializers.Serializer):
    """
    CAV-182: Representa una fila de la lista de usuarios autorizados
    que se sincroniza de forma incremental al dispositivo movil.
    No incluye password ni ningun dato sensible: solo lo minimo
    necesario para que el cliente sepa "quien esta autorizado".
    """
    dni = serializers.CharField()
    username = serializers.CharField()
    nombre_completo = serializers.CharField()
    activo = serializers.BooleanField()
    actualizado_en = serializers.DateTimeField()


class EventoLoginOfflineSerializer(serializers.Serializer):
    """
    CAV-83: payload que manda el celular al reportar (una vez que
    recupera conexion) que hubo un inicio de sesion validado localmente
    mientras estaba sin señal.
    """
    device_id = serializers.CharField(max_length=255)
    fecha_hora_offline = serializers.DateTimeField()


class ConfiguracionToleranciaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    tipo_horario_display = serializers.CharField(source='get_tipo_horario_display', read_only=True)

    class Meta:
        model = ConfiguracionTolerancia
        fields = [
            'id', 'sede', 'sede_nombre', 'tipo_horario', 'tipo_horario_display',
            'minutos_tolerancia', 'activo', 'creado_en', 'actualizado_en',
        ]
        read_only_fields = ['id', 'sede_nombre', 'tipo_horario_display', 'creado_en', 'actualizado_en']

    def validate_minutos_tolerancia(self, value):
        if value < 0:
            raise serializers.ValidationError("Los minutos de tolerancia no pueden ser negativos.")
        if value > 180:
            raise serializers.ValidationError("Los minutos de tolerancia no pueden superar 180.")
        return value
