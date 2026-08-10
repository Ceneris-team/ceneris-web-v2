from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import datetime

# ==========================================
# 1. CATÁLOGOS (La base de datos estática)
# ==========================================

class GerenciaGeneral(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self): return self.nombre

class Gerencia(models.Model):
    gerencia_general = models.ForeignKey(GerenciaGeneral, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    def __str__(self): return self.nombre

class Superintendencia(models.Model):
    gerencia = models.ForeignKey(Gerencia, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    def __str__(self): return self.nombre

class Puesto(models.Model):
    superintendencia = models.ForeignKey(Superintendencia, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    def __str__(self): return self.nombre

class Agente(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    def __str__(self): return self.nombre

class Cargo(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self): return self.nombre

class Trabajador(models.Model):
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores'
    )

    nombre = models.CharField(
        max_length=100
    )

    ap_paterno = models.CharField(
        max_length=100
    )

    ap_materno = models.CharField(
        max_length=100
    )

    dni = models.CharField(
        max_length=8,
        unique=True
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    correo = models.EmailField(
        blank=True,
        null=True
    )

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.ap_paterno} {self.ap_materno}".strip()

    def __str__(self):
        return self.nombre_completo

    class Meta:
        ordering = ['ap_paterno', 'ap_materno', 'nombre']
        verbose_name = 'Trabajador'
        verbose_name_plural = 'Trabajadores'

# ==========================================
# 2. EL PROCESO (Programación en Cascada)
# ==========================================

class ProgramacionMensual(models.Model):
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE)
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE)
    mes = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    anio = models.IntegerField(default=datetime.date.today().year)
    cantidad_mes = models.IntegerField(default=0)
    responsable_mes = models.ForeignKey(Trabajador, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"MENSUAL {self.mes}/{self.anio}: {self.puesto} - {self.agente}"

class ProgramacionSemanal(models.Model):
    programacion_mensual = models.ForeignKey(ProgramacionMensual, on_delete=models.CASCADE)
    numero_semana = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    cantidad_semanal = models.IntegerField(default=0)
    responsable_semana = models.ForeignKey(Trabajador, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"SEMANA {self.numero_semana} (Meta: {self.cantidad_semanal})"

class ProgramacionDiaria(models.Model):
    # Aquí aplicamos tu lógica: Vinculado a la semana.
    # blank=True permite crear una hoja "suelta" para emergencias puras si fuera necesario
    programacion_semanal = models.ForeignKey(ProgramacionSemanal, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_programacion = models.DateField()
    responsable_diario = models.ForeignKey(Trabajador, on_delete=models.SET_NULL, null=True)
    contacto = models.CharField(max_length=200, blank=True, null=True) # Texto libre o FK según prefieras
    cantidad_diaria = models.IntegerField(default=0)

    def __str__(self):
        return f"DIARIO {self.fecha_programacion} - {self.contactos}"

class DetalleDiario(models.Model):
    programacion = models.ForeignKey(ProgramacionDiaria, on_delete=models.CASCADE, related_name='detalles')
    
    # Vinculación directa a la meta semanal para facilitar consultas
    plan_semanal = models.ForeignKey(ProgramacionSemanal, on_delete=models.SET_NULL, null=True, blank=True, related_name='detalles_diarios')

    # Aquí están los campos clave para soportar "No Planeados" distintos a la cabecera
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE)
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE)
    cantidad_programada = models.IntegerField(default=1, verbose_name="Cantidad Asignada")
    es_planeado = models.BooleanField(default=True)
    
    lugar = models.CharField(max_length=200, blank=True)
    hora = models.TimeField(blank=True, null=True)
    
    monitoristas_asignados = models.ManyToManyField(Trabajador, related_name='tareas')
    
    # Estados y Resultados
    ESTADOS = [('PENDIENTE','Pendiente'), ('EJECUTADO','Ejecutado')]
    estado_tarea = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    cantidad_real_ejecutada = models.IntegerField(default=0)
    hora_fin_real = models.TimeField(blank=True, null=True)
    observacion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.puesto} - {self.agente} ({self.estado_tarea})"

# ==========================================
# 2. SOPORTE TÉCNICO
# ==========================================

class Cliente(models.Model):
    razon_social = models.CharField(max_length=200)
    direccion = models.TextField()
    contacto = models.CharField(max_length=100)
    correo = models.EmailField()

    def __str__(self):
        return self.razon_social

class Proveedor(models.Model):
    # Asumo que Trabajador es un modelo existente
    trabajador = models.ForeignKey('Trabajador', on_delete=models.CASCADE, verbose_name="Trabajador Responsable")
    telefono = models.CharField(max_length=20)
    contacto = models.CharField(max_length=100)
    correo = models.EmailField()

    def __str__(self):
        return f"{self.contacto} - {self.trabajador}"
    
class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Dispositivo(models.Model):

    ESTADOS = [
        ('OPERATIVO', 'Operativo'),
        ('INOPERATIVO', 'Inoperativo'),
        ('PRESTADO', 'Prestado'),
        ('CALIBRACION_VENCIDA', 'Calibración Vencida'),
        ('BAJA', 'Baja'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='dispositivos'
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='dispositivos'
    )

    nombre = models.CharField(max_length=100)

    marca = models.CharField(max_length=50)

    modelo = models.CharField(max_length=50)

    codigo_modelo = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    serie = models.CharField(max_length=100)

    codigo_interno = models.CharField(
        max_length=50,
        unique=True
    )

    uso = models.CharField(
        max_length=100,
        default='Monitoreo Industrial'
    )

    pais_fabricacion = models.CharField(
        max_length=50,
        default='No especificado'
    )

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='OPERATIVO'
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_bajada = models.DateField(
        blank=True,
        null=True
    )

    fecha_subida = models.DateField(
        blank=True,
        null=True
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.codigo_interno} - {self.nombre}"

    class Meta:
        ordering = ['codigo_interno']

class Accesorio(models.Model):

    TIPOS = [
        ('ACCESORIO', 'Accesorio'),
        ('COMPONENTE', 'Componente'),
        ('SENSOR', 'Sensor'),
        ('MICROFONO', 'Micrófono'),
    ]

    ESTADOS = [
        ('OPERATIVO', 'Operativo'),
        ('REGULAR', 'Regular'),
        ('DANIADO', 'Dañado'),
        ('BAJA', 'Baja'),
    ]

    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='accesorios'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='ACCESORIO'
    )

    nombre = models.CharField(
        max_length=100
    )

    serie = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    codigo_inventario = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='OPERATIVO'
    )

    activo = models.BooleanField(
        default=True
    )

    # Campos de sensibilidad (aplica a sensores de vibrómetro)
    eje_x = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Sensibilidad Eje X"
    )

    eje_y = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Sensibilidad Eje Y"
    )

    eje_z = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Sensibilidad Eje Z"
    )

    def __str__(self):
        return f"{self.dispositivo.codigo_interno} - {self.nombre}"

    class Meta:
        ordering = ['nombre']

# --- MÓDULO DE DIAGNÓSTICO ---

class Diagnostico(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    estado = models.CharField(max_length=500)
    diagnostico = models.TextField()
    fecha_manufactura = models.DateField(null=True, blank=True)
    recomendaciones = models.TextField()
    numero = models.CharField(max_length=50, unique=True) # Número de reporte
    fecha_recepcion = models.DateField(default=timezone.now)
    fecha_revision = models.DateField(default=timezone.now)

class FotoDiagnostico(models.Model):
    diagnostico = models.ForeignKey(Diagnostico, on_delete=models.CASCADE, related_name='fotos')
    img = models.ImageField(upload_to='soporte/diagnosticos/')
    descripcion = models.TextField()
# --- MÓDULO DE MANTENIMIENTO ---

class Mantenimiento(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    equipo_contraste = models.CharField(max_length=100)
    trabajo = models.TextField() # Descripción del trabajo realizado
    estado_final = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

# --- MÓDULO DE OPERATIVIDAD ---

class Operatividad(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    estado_inicial = models.CharField(max_length=50)
    estado_final = models.CharField(max_length=50)
    fecha_recepcion = models.DateField(default=timezone.now)
    fecha_operatividad = models.DateField()

class Verificacion(models.Model):
    operatividad = models.ForeignKey(Operatividad, on_delete=models.CASCADE, related_name='verificaciones')
    pregunta = models.CharField(max_length=200)
    respuesta = models.CharField(max_length=200)

class Evidencias(models.Model):
    operatividad = models.ForeignKey(Operatividad, on_delete=models.CASCADE, related_name='evidencias')
    img = models.ImageField(upload_to='soporte/evidencias/')
    descripcion = models.TextField()

# --- MÓDULO DE CALIBRACIÓN ---

class Calibracion(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    estado_inicial = models.CharField(max_length=50)
    estado_final = models.CharField(max_length=50)
    fecha_recepcion = models.DateField()
    fecha_calibracion = models.DateField(default=timezone.now)
    fecha_proxima = models.DateField(null=True, blank=True)

class Patrones(models.Model):
    calibracion = models.ForeignKey(Calibracion, on_delete=models.CASCADE, related_name='patrones')
    
    # CAMBIO: Ahora vinculamos a un Dispositivo real
    equipo_patron = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, verbose_name="Equipo Patrón")
    
    # Mantenemos esto para indicar la fuente (ej: NIST, SNM)
    trazabilidad = models.CharField(max_length=100, default="Patrón Nacional", blank=True, null=True)

    def __str__(self):
        return f"Patrón: {self.equipo_patron.nombre} para Calib #{self.calibracion.id}"

class Resultados(models.Model):
    calibracion = models.ForeignKey(Calibracion, on_delete=models.CASCADE, related_name='resultados')
    flujo_nominal = models.DecimalField(max_digits=10, decimal_places=4)
    flujo_establecido = models.DecimalField(max_digits=10, decimal_places=4)
    lectura_promedio = models.DecimalField(max_digits=10, decimal_places=4)
    desviacion = models.DecimalField(max_digits=10, decimal_places=4)
    icertidumbre = models.DecimalField(max_digits=10, decimal_places=4)
    condicion = models.CharField(max_length=50) # Pasa / No Pasa
    m1 = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    m2 = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    m3 = models.DecimalField(max_digits=10, decimal_places=4, default=0)

class FotoPatron(models.Model):
    calibracion = models.ForeignKey(Calibracion, on_delete=models.CASCADE)
    img = models.ImageField(upload_to='soporte/patrones/')

# --- MÓDULO DE INVENTARIO DE REPUESTOS ---
class InventarioRepuestos(models.Model):
    proyecto = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    equipo = models.CharField(max_length=100) # Ej. Vibrometro
    articulo = models.CharField(max_length=100) # Ej. Cable 010AYCA
    codigo = models.CharField(max_length=50, unique=True) # Código único para vincular
    stock = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.articulo} ({self.codigo}) - Stock: {self.stock}"

# --- MÓDULO DE CAMBIO DE COMPONENTES ---

class HistorialCambioAccesorio(models.Model):

    accesorio = models.ForeignKey(
        Accesorio,
        on_delete=models.CASCADE,
        related_name='historial_cambios'
    )

    fecha_cambio = models.DateField()

    proximo_cambio = models.DateField(
        blank=True,
        null=True
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.accesorio.nombre} - "
            f"{self.fecha_cambio}"
        )

    class Meta:
        ordering = ['-fecha_cambio']

# ==========================================
# 1. PLANIFICACIÓN
# ==========================================

class ProgramaMantenimiento(models.Model):
    anio = models.IntegerField(default=2025, verbose_name="Año")
    nombre = models.CharField(max_length=200, default="PROGRAMA DE INSPECCION")
    semestre = models.IntegerField(default=1, choices=[(1, 'Primer Semestre'), (2, 'Segundo Semestre')])
    
    def __str__(self):
        return f"{self.nombre} {self.anio} - Semestre {self.semestre}"

class FilaCronograma(models.Model):
    """
    Representa una fila del PDF (Ej: Item N° 1).
    Contiene la fecha P (Programada) y la fecha E (Ejecutada).
    """
    programa = models.ForeignKey(ProgramaMantenimiento, on_delete=models.CASCADE, related_name='filas')
    numero = models.IntegerField(verbose_name="N°")
    
    # FECHAS (Determinan dónde va la 'X')
    fecha_programada = models.DateField()
    ejecutado = models.BooleanField(default=False, verbose_name="¿Ejecutado?")  
    
    # DISPOSITIVOS (Comparación para texto rojo)
    # 1. Los que se suponía que iban a inspeccionarse
    equipos_programados = models.ManyToManyField(Dispositivo, related_name='filas_programadas', blank=True)
    # 2. Los que realmente se inspeccionaron
    equipos_ejecutados = models.ManyToManyField(Dispositivo, related_name='filas_ejecutadas', blank=True)
    
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f"Fila {self.numero} - {self.fecha_programada}"


# ==========================================
# 2. EJECUCIÓN: CABECERA
# ==========================================

class Inspeccion(models.Model):
    """
    La hoja de inspección que agrupa varios equipos en un solo día.
    """
    codigo_documento = models.CharField(max_length=50, default="CEN-PY-MCV-PR-08-PG-01")
    fecha_inspeccion = models.DateField(default=timezone.now)
    responsable = models.ForeignKey(Trabajador, on_delete=models.SET_NULL, null=True, verbose_name="Responsable de Inspección")
    
    # Totales para el reporte resumen
    total_equipos = models.IntegerField(default=0)
    equipos_en_campo = models.IntegerField(default=0)
    cant_muestra = models.IntegerField(default=0)
    
    observaciones_generales = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Dosímetros
    dosi_operatividad = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    dosi_limpieza = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    dosi_accesorios = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    dosi_obs = models.CharField(max_length=200, blank=True, verbose_name="Obs Dosímetros")

    # Bombas
    bomba_operatividad = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    bomba_limpieza = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    bomba_accesorios = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    bomba_obs = models.CharField(max_length=200, blank=True, verbose_name="Obs Bombas")

    # Vibrómetros
    vibro_operatividad = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    vibro_limpieza = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    vibro_accesorios = models.CharField(max_length=2, default="SI", choices=[('SI','SI'), ('NO','NO'), ('', '-')])
    vibro_obs = models.CharField(max_length=200, blank=True, verbose_name="Obs Vibrómetros")

    def __str__(self):
        return f"Inspección {self.id} - {self.fecha_inspeccion}"


# ==========================================
# 3. EJECUCIÓN: DETALLE POR EQUIPO
# ==========================================

class DetalleInspeccion(models.Model):
    """
    El chequeo individual de CADA equipo dentro de una Inspección.
    """
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='detalles')
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    
    # --- CHECKLIST ESTADO FÍSICO (Imagen 1) ---
    # Opciones: Bueno, Malo, No Aplica
    ESTADO_OPCIONES = [('B', 'Bueno'), ('M', 'Malo'), ('NA', 'No Aplica')]
    
    estado_case = models.CharField(max_length=2, choices=ESTADO_OPCIONES, default='B')
    estado_botones = models.CharField(max_length=2, choices=ESTADO_OPCIONES, default='B')
    estado_pantalla = models.CharField(max_length=2, choices=ESTADO_OPCIONES, default='B')
    estado_bateria = models.CharField(max_length=2, choices=ESTADO_OPCIONES, default='B')
    estado_accesorios = models.CharField(max_length=2, choices=ESTADO_OPCIONES, default='B')
    
    # --- CHECKLIST RÁPIDO (Imagen 2) ---
    limpieza = models.BooleanField(default=True, verbose_name="Limpieza OK")
    operatividad = models.BooleanField(default=True, verbose_name="Operatividad OK")
    
    observaciones = models.TextField(blank=True, null=True)
    
    # Resultado Final del Equipo en esta inspección
    resultado_final = models.CharField(max_length=50, default="Operativo") # Operativo / Inoperativo


# ==========================================
# 4. PRUEBAS TÉCNICAS
# ==========================================

class PruebaTecnica(models.Model):
    """
    Datos numéricos de calibración y tiempos (Imagen 1 - Parte inferior)
    Se vincula al DetalleInspeccion (Uno a Uno).
    """
    detalle_inspeccion = models.OneToOneField(DetalleInspeccion, on_delete=models.CASCADE, related_name='prueba_tecnica')
    
    # Tiempos
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    tiempo_total = models.CharField(max_length=50, blank=True, null=True) # Ej: "07h 44min"
    
    # --- CAMPOS PARA BOMBAS (Flujo) ---
    flujo_pre_calibracion = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    flujo_post_calibracion = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    flujo_promedio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, verbose_name="Promedio L/m")
    
    # --- CAMPOS PARA DOSÍMETROS (Ruido dB) ---
    db_pre_calibracion = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    db_post_calibracion = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    respuesta = models.CharField(max_length=20, blank=True, null=True)  
    tasa_cambio = models.CharField(max_length=20, default="3 dB", blank=True)
    ponderacion = models.CharField(max_length=20, default="A", blank=True)
    
    # Lecturas Dosímetro
    l_max = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    l_min = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    l_pico = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    # --- CAMPOS PARA VIBRÓMETROS (Sensibilidad) ---
    # Si se verifican en la inspección
    serie_cuerpo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Serie Cuerpo")
    sens_x_cuerpo = models.CharField(max_length=20, blank=True, null=True)
    sens_y_cuerpo = models.CharField(max_length=20, blank=True, null=True)
    sens_z_cuerpo = models.CharField(max_length=20, blank=True, null=True)

    # Lado Derecho: Mano Brazo
    serie_mano = models.CharField(max_length=50, blank=True, null=True, verbose_name="Serie Mano")
    sens_x_mano = models.CharField(max_length=20, blank=True, null=True)
    sens_y_mano = models.CharField(max_length=20, blank=True, null=True)
    sens_z_mano = models.CharField(max_length=20, blank=True, null=True)
    fuentes_ruido = models.CharField(max_length=200, blank=True, null=True)

    # --- EQUIPO PATRÓN USADO ---
    # Vinculamos al dispositivo patrón interno (ej: Calibrador Acústico)
    equipo_patron = models.ForeignKey(Dispositivo, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspecciones_como_patron')

    # --- CAMPOS NUEVOS PARA "RESULTADOS" ---
    
    # 1. BOMBA: Preguntas Sí/No
    # Usaremos CharField para guardar "SI" o "NO"
    bomba_flujo_constante = models.CharField(max_length=2, default="SI", blank=True)
    bomba_ruido_excesivo = models.CharField(max_length=2, default="NO", blank=True)

    # 2. VIBRÓMETRO: Niveles AEQ
    vibro_aeq_x = models.CharField(max_length=20, blank=True, null=True, verbose_name="AEQ X")
    vibro_aeq_y = models.CharField(max_length=20, blank=True, null=True, verbose_name="AEQ Y")
    vibro_aeq_z = models.CharField(max_length=20, blank=True, null=True, verbose_name="AEQ Z")

    no_aplica = models.BooleanField(default=False, verbose_name="No Aplica Calibración")

class InspeccionPatron(models.Model):
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='patrones_usados')
    patron = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, verbose_name="Equipo Patrón")
    observacion = models.CharField(max_length=200, default="Equipo operativo y con certificación vigente.")

class EquipoReportado(models.Model):
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='equipos_reportados')
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    fecha_reporte = models.DateField(default=timezone.now)
    motivo = models.CharField(max_length=200)
    estado = models.CharField(max_length=50, default="Inoperativo")