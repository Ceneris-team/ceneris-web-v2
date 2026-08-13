from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings

from .motor_reglas import EstadoMarca

# Validador para DNI
dni_validator = RegexValidator(
    regex=r'^\d{8}$',
    message='El DNI debe tener exactamente 8 dígitos numéricos.'
)

class Empresa(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Empresa")
    ruc = models.CharField(max_length=11, unique=True, blank=True, null=True, verbose_name="RUC")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de Contacto")
    email_contacto = models.EmailField(blank=True, null=True, verbose_name="Email de Contacto")
    persona_contacto = models.CharField(max_length=150, blank=True, null=True, verbose_name="Persona de Contacto")

    def __str__(self):
        return self.nombre

class Ubicacion(models.Model):
        nombre = models.CharField(max_length=150, unique=True)
        # Dejamos la hora de entrada que tenías en tu formulario original
        hora_entrada = models.TimeField(null=True, blank=True, verbose_name="Hora de Entrada")
        
        # Hacemos estos campos obligatorios para asegurar que siempre sea un círculo
        latitud = models.FloatField(default=0.0)
        longitud = models.FloatField(default=0.0)
        radio = models.PositiveIntegerField(default=50, help_text="Radio en metros")
        
        creado_en = models.DateTimeField(auto_now_add=True)
        actualizado_en = models.DateTimeField(auto_now=True)
    
        def __str__(self):
            return self.nombre
    
        class Meta:
            verbose_name = "Ubicación"
            verbose_name_plural = "Ubicaciones"

class Proyecto(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre del Proyecto")
    codigo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código del Proyecto")
    
    # --- ¡CAMBIO 1: HACER EL CAMPO OPCIONAL! ---
    # Añadimos null=True y blank=True para que un subproyecto no necesite
    # que se le asigne una empresa explícitamente en el formulario.
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proyectos', null=True, blank=True)
    
    cliente = models.CharField(max_length=100, blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, 
        blank=True, related_name='subproyectos', verbose_name="Proyecto Padre"
    )

    # --- ¡CAMBIO 2: LÓGICA DE GUARDADO AUTOMÁTICO! ---w
    def save(self, *args, **kwargs):
        # Si este es un subproyecto (tiene un 'parent') y no se le ha asignado una empresa...
        if self.parent and not self.empresa:
            # ...hereda automáticamente la empresa del proyecto padre.
            self.empresa = self.parent.empresa
        super().save(*args, **kwargs) # Llama al método de guardado original

    def __str__(self):
        if self.parent:
            return f"{self.parent.nombre} -> {self.nombre}"
        return self.nombre

class CentroCosto(models.Model):
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código (ej. K400)")
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Centro de Costo")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Cargo(models.Model):
    codigo = models.CharField(max_length=10, unique=True, blank=True, null=True, verbose_name="Código de Cargo")
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Cargo")
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Area(models.Model):
    # --- NUEVO CAMPO ---
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Código de Área")
    
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Área")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}" if self.codigo else self.nombre

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        ordering = ['nombre']

class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Sede")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="Activa")
    
    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Trabajador(models.Model):
    class CargoJerarquico(models.TextChoices):
        TRABAJADOR = 'TRABAJADOR', 'Trabajador'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        RESPONSABLE = 'RESPONSABLE', 'Responsable'
        GERENTE = 'GERENTE', 'Gerente'

    # --- Datos de Identificación ---
    dni = models.CharField(max_length=8, unique=True, validators=[dni_validator])
    apellido_paterno = models.CharField(max_length=100, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=100, verbose_name="Apellido Materno")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # Ubicaciones permitidas: relación Muchos-a-Muchos entre Trabajador y Ubicacion
    ubicaciones_permitidas = models.ManyToManyField(
        'Ubicacion',
        related_name='trabajadores',
        blank=True,
        verbose_name='Ubicaciones Permitidas'
    )
    
    # --- CAMBIO CLAVE: Eliminamos 'cargo' y 'proyecto_actual' directos ---
    # Ahora usamos una relación Muchos-a-Muchos a través de una tabla intermedia
    proyectos = models.ManyToManyField(
        Proyecto, 
        through='AsignacionProyecto', 
        related_name='trabajadores'
    )
    area = models.ForeignKey(
        Area, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Área Asignada"
    )
    areas_supervisadas = models.ManyToManyField(
        Area,
        blank=True,
        related_name='jefes_supervisores',
        verbose_name='Áreas Supervisadas (Jefatura)'
    )
    cargo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Cargo Fijo/Principal")
    sede = models.ForeignKey(
        Sede,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores',
        verbose_name="Sede Asignada"
    )
    es_jefe = models.BooleanField(default=False)
    es_gerente = models.BooleanField(default=False, verbose_name="Es Gerente General")
    # Fechas de ingreso A LA EMPRESA (Ceneris), no al proyecto
    fecha_ingreso = models.DateField(null=True, blank=True, verbose_name="Fecha de Ingreso Empresa")
    fecha_cese = models.DateField(null=True, blank=True, verbose_name="Fecha de Cese Empresa")
    
    # --- Datos Personales ---
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(max_length=10, choices=[('M', 'Masculino'), ('F', 'Femenino')], blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True)

    # Estado Global
    aptitud_actual = models.CharField(max_length=50, default='Sin Evaluación', editable=False)
    activo = models.BooleanField(default=True)

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno}".strip()

    @property
    def cargo_jerarquico(self):
        if self.es_jefe and self.es_gerente:
            return self.CargoJerarquico.RESPONSABLE
        if self.es_gerente:
            return self.CargoJerarquico.GERENTE
        if self.es_jefe:
            return self.CargoJerarquico.SUPERVISOR
        return self.CargoJerarquico.TRABAJADOR

    @property
    def cargojerarquico(self):
        # Alias solicitado para uso en vistas/plantillas.
        return self.cargo_jerarquico

    @property
    def cargo_jerarquico_label(self):
        return self.CargoJerarquico(self.cargo_jerarquico).label

    def set_cargo_jerarquico(self, cargo_jerarquico):
        cargo = (cargo_jerarquico or self.CargoJerarquico.TRABAJADOR).upper()

        if cargo == self.CargoJerarquico.GERENTE:
            self.es_jefe = False
            self.es_gerente = True
        elif cargo == self.CargoJerarquico.RESPONSABLE:
            self.es_jefe = True
            self.es_gerente = True
        elif cargo == self.CargoJerarquico.SUPERVISOR:
            self.es_jefe = True
            self.es_gerente = False
        else:
            self.es_jefe = False
            self.es_gerente = False

    def __str__(self):
        return f"{self.apellido_paterno} {self.apellido_materno}, {self.nombres}"
    @property
    def estado_emo_actual(self):
        ultimo_emo = self.historial_emo.filter(estado='Realizado').order_by('-fecha_realizacion', '-pk').first()
        if not ultimo_emo:
            if self.historial_emo.filter(estado='Programado').exists():
                return "EMO Pendiente"
            return "Sin EMO"
        if ultimo_emo.fecha_vencimiento < timezone.now().date():
            return "EMO Vencido"
        return "Vigente"
    
    def obtener_cumplimiento_total(self):
        """
        Calcula el promedio de todas las evaluaciones del trabajador.
        Requiere que exista el modelo EvaluacionMensual con related_name='evaluaciones'.
        """
        try:
            evaluaciones = self.evaluaciones.all()
            if not evaluaciones.exists():
                return 0
            total = sum([ev.promedio_final for ev in evaluaciones])
            return round(total / evaluaciones.count(), 1)
        except AttributeError:
            # Si no existe la relación 'evaluaciones', devolver 0
            return 0

class AsignacionProyecto(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='asignaciones')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='asignaciones')
    
    # El CARGO ahora depende de la asignación. 
    # Puede ser "Supervisor" en un proyecto y "Asistente" en otro.
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name="Inicio en Proyecto")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fin en Proyecto")
    activo = models.BooleanField(default=True, verbose_name="Activo en este proyecto")

    class Meta:
        verbose_name = "Asignación de Proyecto"
        verbose_name_plural = "Asignaciones de Proyectos"
        # Opcional: Evita duplicar la misma persona en el mismo proyecto dos veces
        unique_together = ('trabajador', 'proyecto') 

    def __str__(self):
        cargo_nombre = self.cargo.nombre if self.cargo else "Sin Cargo"
        return f"{self.trabajador} -> {self.proyecto} ({cargo_nombre})"

class Cuestionario(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nombre

class Pregunta(models.Model):
    cuestionario = models.ForeignKey(Cuestionario, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.TextField(unique=True)
    orden = models.PositiveIntegerField(default=0)
    clave_puntuacion = models.CharField(max_length=50, blank=True, null=True, help_text="Ej: 'D', 'I', 'S', 'C', 'Extroversión+', 'Afrontamiento_Activo'")
    class Meta: ordering = ['cuestionario', 'orden']
    def __str__(self): return f"{self.cuestionario.nombre} - {self.texto[:50]}..."

class ResultadoCuestionario(models.Model):
    trabajador = models.ForeignKey('Trabajador', on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    timestamp = models.DateTimeField()
    puntuaciones = models.JSONField(null=True, blank=True)
    def __str__(self): return f"Resultado de {self.email} - {self.timestamp.strftime('%d/%m/%Y')}"

class Respuesta(models.Model):
    resultado = models.ForeignKey(ResultadoCuestionario, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    valor = models.CharField(max_length=255)
    def __str__(self): return f"Respuesta a '{self.pregunta.texto[:30]}...': {self.valor}"


class SolicitudHorasExtra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_OPERADOR = 'PENDIENTE_OPERADOR', 'Pendiente de Operador'
        PENDIENTE_ADMIN = 'PENDIENTE_ADMIN', 'Pendiente de Administrador'
        PENDIENTE_GERENTE = 'PENDIENTE_GERENTE', 'Pendiente de Gerente'
        APROBADO = 'APROBADO', 'Aprobado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'

    # --- DATOS DE LA SOLICITUD ---
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='solicitudes_horas_extra')
    fecha_horas_extra = models.DateField(help_text="El día en que se realizaron las horas extra.")
    cantidad_horas = models.DecimalField(max_digits=4, decimal_places=2, help_text="Ej: 2.5 para 2 horas y media.")
    justificacion = models.TextField(verbose_name="Justificación del Trabajador")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE_OPERADOR)
    
    # --- DATOS DE AUDITORÍA ---
    creado_en = models.DateTimeField(auto_now_add=True)
    solicitado_desde_app = models.BooleanField(default=True) # Para diferenciar de las creadas manualmente

    aprobado_por_operador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='horas_aprobadas_operador')
    fecha_aprobacion_operador = models.DateTimeField(null=True, blank=True)
    
    aprobado_por_admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='horas_aprobadas_admin')
    fecha_aprobacion_admin = models.DateTimeField(null=True, blank=True)

    aprobado_por_gerente = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='horas_aprobadas_gerente')
    fecha_aprobacion_gerente = models.DateTimeField(null=True, blank=True)
    
    motivo_rechazo = models.TextField(blank=True)

    def __str__(self):
        return f"Solicitud de {self.cantidad_horas}h para {self.trabajador} el {self.fecha_horas_extra}"

    class Meta:
        ordering = ['-fecha_horas_extra']

class Asistencia(models.Model):
    # Relacionamos la asistencia con el usuario (trabajador) que la registró
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias")
    
    timestamp = models.DateTimeField(help_text="Fecha y hora exactas de la marcación")
    tipo_marcacion = models.CharField(max_length=10, choices=[('Entrada', 'Entrada'), ('Salida', 'Salida')])
    
    # Guardamos latitud y longitud como números de punto flotante
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    
    nombre_ubicacion = models.CharField(max_length=255, null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    
    origen = models.CharField(
        max_length=20, 
        choices=[('APP', 'Aplicación Móvil'), ('BIOMETRICO', 'Reloj Biométrico'), ('MANUAL', 'Manual')],
        default='APP',
        verbose_name="Medio de Marcación"
    )

    # Este campo se llenará automáticamente con la fecha y hora de creación del registro en la BD
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        # Esto es para que se vea bonito en el panel de administrador de Django
        return f"{self.usuario.username} - {self.tipo_marcacion} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        # Ordena las asistencias de la más reciente a la más antigua por defecto
        ordering = ['-timestamp']


class IntentoFraude(models.Model):
    trabajador = models.ForeignKey('Trabajador', on_delete=models.CASCADE, related_name='alertas_fraude')
    
    # Datos del incidente
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora del Intento")
    motivo_detectado = models.CharField(max_length=255, help_text="Ej: Uso de VPN, Ubicación Falsa (Mock), Root")
    
    # Evidencia técnica
    device_id = models.CharField(max_length=255, null=True, blank=True)
    latitud_reportada = models.FloatField(null=True, blank=True)
    longitud_reportada = models.FloatField(null=True, blank=True)
    
    # Gestión de RRHH
    revisado = models.BooleanField(default=False, verbose_name="Revisado por RRHH")
    comentarios_rrhh = models.TextField(blank=True, null=True, help_text="Medidas tomadas con el trabajador")

    class Meta:
        verbose_name = "Intento de Fraude"
        verbose_name_plural = "Intentos de Fraude"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"ALERTA: {self.trabajador.nombre_completo} - {self.motivo_detectado}"

class Dispositivo(models.Model):
    # Usamos el ID del dispositivo como clave primaria. Es único y lo envía la app.
    id = models.CharField(primary_key=True, max_length=255, help_text="ID único del dispositivo (de Android/iOS)")
    nombre = models.CharField(max_length=200, help_text="Nombre descriptivo, ej: Dispositivo de Juan Pérez")
    
    # Relación Muchos-a-Muchos: Un dispositivo puede tener muchos trabajadores permitidos.
    trabajadores_permitidos = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="dispositivos_permitidos",
        blank=True, # Un dispositivo puede no tener a nadie asignado al principio
        verbose_name="Trabajadores Permitidos"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.id})"

class TareoDiario(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='dias_tareo')
    fecha = models.DateField(db_index=True)
    
    # Estado: 'C' (Campo), 'O' (Oficina), 'F' (Falta), etc.
    estado = models.CharField(max_length=5) 
    resultado = models.CharField(
        max_length=5, 
        default='F', # <--- AQUÍ ESTÁ TU REGLA DE ORO: Nace como Falta
        verbose_name="Resultado Asistencia"
    )
    # Para horario personalizado (P)
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    
    # Para jornada por horas (J)
    jornada_horas = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    # --- 2. HORARIO REAL (EJECUCIÓN) ---
    # Aquí guardaremos la primera marcación y la última marcación del modelo Asistencia
    hora_entrada_real = models.TimeField(null=True, blank=True, verbose_name="Primera Marcación")
    hora_salida_real = models.TimeField(null=True, blank=True, verbose_name="Última Marcación")
    
    horas_trabajadas_validas = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.00, 
        verbose_name="Horas Válidas (Pago)"
    )
    
    horas_tardanza = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Tardanza (Hrs)"
    )
    
    # Para saber si se aplicó descuento automático de almuerzo
    descuento_almuerzo_aplicado = models.BooleanField(default=False)

    # Clasificación de la marca del día que produce el motor de reglas
    # (CAV-167): NORMAL, TARDANZA, FERIADO, FUERA_HORARIO, etc. Es distinto de
    # `estado` (tipo de jornada) y de `resultado` (F/A/J). Nace en null hasta
    # que el motor evalúa el día.
    etiqueta_estado = models.CharField(
        max_length=20,
        choices=EstadoMarca.choices,
        null=True,
        blank=True,
        verbose_name="Etiqueta de la marca",
    )

    # Opcional: Ubicación asignada
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def origen(self):
        """Busca la primera asistencia de este día para saber por dónde marcó"""
        if not self.trabajador.user:
            return None

        # Asistencia.Meta.ordering = ['-timestamp'] (descendente). Sin este
        # order_by explícito, .first() devolvía la ÚLTIMA marca del día en
        # vez de la primera, al revés de lo que dice este método.
        primera_asistencia = Asistencia.objects.filter(
            usuario=self.trabajador.user,
            timestamp__date=self.fecha
        ).order_by('timestamp').first()

        if primera_asistencia:
            return primera_asistencia.origen
        return None

    @property
    def hora_entrada_real_calculada(self):
        """
        Hora de entrada real calculada EN VIVO desde Asistencia (la marca de
        tipo Entrada mas temprana del dia), en vez de leer el campo guardado
        hora_entrada_real. Esto evita mostrar un dato viejo/incorrecto que
        haya quedado congelado en la base de datos por una sincronizacion
        anterior; siempre refleja la marcacion real, sin importar cuando se
        haya registrado.
        """
        if not self.trabajador.user_id:
            return self.hora_entrada_real

        primera_entrada = Asistencia.objects.filter(
            usuario_id=self.trabajador.user_id,
            timestamp__date=self.fecha,
            tipo_marcacion='Entrada',
        ).order_by('timestamp').first()

        if primera_entrada:
            return timezone.localtime(primera_entrada.timestamp).time()
        return self.hora_entrada_real

    @property
    def hora_salida_real_calculada(self):
        """Igual que hora_entrada_real_calculada, pero con la marca de Salida
        mas tardia del dia."""
        if not self.trabajador.user_id:
            return self.hora_salida_real

        ultima_salida = Asistencia.objects.filter(
            usuario_id=self.trabajador.user_id,
            timestamp__date=self.fecha,
            tipo_marcacion='Salida',
        ).order_by('-timestamp').first()

        if ultima_salida:
            return timezone.localtime(ultima_salida.timestamp).time()
        return self.hora_salida_real

    @property
    def resultado_efectivo(self):
        """
        Estado real del día, resolviendo el caso en que el campo `resultado`
        quedó desactualizado (ej. marcaciones cargadas directamente en la
        base de datos, que no pasan por el recálculo automático y dejaban el
        día como 'F' aunque existieran marcas reales).

        Prioridad: Justificado > marcaciones reales > lo que diga el campo.
        La justificación manda porque la aprueba RRHH o llega del ERP: un día
        de licencia no se convierte en "Asistió" por una marcación suelta.
        """
        guardado = (self.resultado or '').upper()

        if guardado == 'J':
            return 'J'

        if self.trabajador.user_id and Asistencia.objects.filter(
            usuario_id=self.trabajador.user_id,
            timestamp__date=self.fecha,
        ).exists():
            return 'A'

        return guardado or 'F'
    
    class Meta:
        unique_together = ('trabajador', 'fecha') # Un trabajador solo tiene un estado por día
        indexes = [
            models.Index(fields=['fecha', 'trabajador']),
        ]

    def __str__(self):
        return f"{self.trabajador} - {self.fecha}: {self.estado}"

class Justificacion(models.Model):
    MOTIVOS = [
        ('SALUD', 'Salud / Médica'),
        ('PERSONAL', 'Motivos Personales'),
        ('TRAMITE', 'Trámites Administrativos'),
        ('TRANSPORTE', 'Problemas de Transporte'),
        ('OTRO', 'Otro'),
    ]

    # Vinculamos la justificación a un día específico del tareo
    tareo = models.OneToOneField(
        'TareoDiario', 
        on_delete=models.CASCADE, 
        related_name='justificacion',
        limit_choices_to={'resultado': 'F'} # Solo se puede justificar si es Falta
    )
    
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    descripcion = models.TextField(verbose_name="Detalle de la justificación")
    
    # Al usar FileField y tener S3 configurado en settings.py, esto se va directo a la nube
    archivo_evidencia = models.FileField(
        upload_to='justificaciones/%Y/%m/', 
        blank=True, 
        null=True,
        verbose_name="Evidencia (PDF/Foto)"
    )
    
    # Estado de la justificación (para que RRHH la apruebe después)
    estado_solicitud = models.CharField(
        max_length=20, 
        choices=[('PENDIENTE', 'Pendiente'), ('APROBADO', 'Aprobado'), ('RECHAZADO', 'Rechazado')],
        default='PENDIENTE'
    )
    motivo_rechazo = models.TextField(blank=True, verbose_name="Motivo de rechazo RRHH")
    
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Justificación {self.tareo.trabajador} - {self.tareo.fecha}"


class ConfiguracionTolerancia(models.Model):
    """HU-06 (CAV-15): tolerancia de tardanza configurable por Sede y horario/turno."""

    class TipoHorario(models.TextChoices):
        CAMPO = 'C', 'Campo'
        OFICINA = 'O', 'Oficina'
        PERSONALIZADO = 'P', 'Personalizado'
        JORNADA_HORAS = 'J', 'Jornada por Horas'

    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name='tolerancias',
        verbose_name="Sede"
    )
    tipo_horario = models.CharField(
        max_length=1,
        choices=TipoHorario.choices,
        verbose_name="Horario / Turno"
    )
    minutos_tolerancia = models.PositiveIntegerField(
        default=15,
        verbose_name="Minutos de Tolerancia"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Tolerancia"
        verbose_name_plural = "Configuraciones de Tolerancia"
        unique_together = ('sede', 'tipo_horario')
        ordering = ['sede__nombre', 'tipo_horario']

    def __str__(self):
        return f"{self.sede.nombre} - {self.get_tipo_horario_display()}: {self.minutos_tolerancia} min"


class ToleranciaAuditoria(models.Model):
    """Historial de cambios sobre ConfiguracionTolerancia (quién, cuándo, de cuánto a cuánto)."""

    configuracion = models.ForeignKey(
        ConfiguracionTolerancia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias',
        verbose_name="Configuración"
    )
    # Se guardan como snapshot para que el historial siga siendo legible
    # aunque la configuración o la sede asociada se eliminen después.
    sede_nombre = models.CharField(max_length=100, verbose_name="Sede")
    tipo_horario = models.CharField(max_length=1, verbose_name="Horario / Turno")

    minutos_anteriores = models.PositiveIntegerField(verbose_name="Minutos Anteriores")
    minutos_nuevos = models.PositiveIntegerField(verbose_name="Minutos Nuevos")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Modificado por"
    )
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Cambio")

    class Meta:
        verbose_name = "Auditoría de Tolerancia"
        verbose_name_plural = "Auditorías de Tolerancia"
        ordering = ['-creado_en']

    def __str__(self):
        usuario_nombre = self.usuario.username if self.usuario else "Sistema"
        return f"{self.sede_nombre} ({self.get_tipo_horario_display()}): {self.minutos_anteriores}min -> {self.minutos_nuevos}min por {usuario_nombre}"

    def get_tipo_horario_display(self):
        return dict(ConfiguracionTolerancia.TipoHorario.choices).get(self.tipo_horario, self.tipo_horario)

