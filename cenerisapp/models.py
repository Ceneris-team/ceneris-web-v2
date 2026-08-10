from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import calendar
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.conf import settings
import os

class Empresa(models.Model):
    
    abreviacion = models.CharField(max_length=20, null=True, blank=True)
    nombreE = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    departamento = models.CharField(max_length=50, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    ruc = models.CharField(max_length=11, null=True, blank=True)

    def __str__(self):
        return self.nombreE

class AreaTrabajo(models.Model):
    nombreA = models.CharField(max_length=100)
    ubicacionA = models.TextField( null=True, blank=True)

    def __str__(self):
        return self.nombreA

class PuntoExacto(models.Model): 
    area_trabajo = models.ForeignKey(AreaTrabajo, on_delete=models.CASCADE, related_name='puntos_exactos')
    nombre_punto = models.CharField(max_length=255, verbose_name="Nombre del Punto Exacto")

    def __str__(self):
        return f"{self.nombre_punto} ({self.area_trabajo.nombreA})"

class Empleado(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    nomEmpleado = models.CharField(max_length=100, null=True, blank=True)
    puesto = models.CharField(max_length=100, null=True, blank=True)
    dni = models.CharField(max_length=8, unique=True, null=True, blank=True)
    areaTrabajo = models.ForeignKey(AreaTrabajo, on_delete=models.CASCADE, null=True, blank=True,)
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinados')

    def __str__(self):
        # Puedes elegir qué mostrar. El nombre es más amigable.
        return self.nomEmpleado 

class Correo(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    direccion_correo = models.EmailField()

    def __str__(self):
        return self.direccion_correo

class Telefono(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    numero = models.CharField(max_length=15)

    def __str__(self):
        return self.numero

class Dispositivo(models.Model):
    id_dispositivo = models.AutoField(primary_key=True)
    num_serie = models.CharField(max_length=50, unique=True)
    nomDisp = models.CharField(max_length=255)
    id_empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    id_areaTrabajo_fijo = models.ForeignKey(
        AreaTrabajo,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Ubicación Permanente (solo para Fijos)"
    )
    tipoDisp = models.CharField(
        max_length=15,
        choices=[
            ('Fijo','Fijo'),
            ('Portatil','Portatil')
        ]
    )
    tag = models.CharField(max_length=50,unique=True, null=False, blank=True)
    estadoD = models.CharField(max_length=50, choices=[('Operativo', 'Operativo'), ('Inoperativo', 'Inoperativo'), ('Extraviado', 'Extraviado')],null=True, blank=True)
    marca = models.CharField(max_length=50, null=True, blank=False)
    fabDisp = models.CharField(max_length=40, unique=False , null =True)
    fecIngreso = models.DateField(null=True, blank=True)
    fecVencimientoGarantia = models.DateField(null=True, blank=True)
    fecFabricacion = models.CharField(max_length=50, null=True, blank=True)
    alarmaPortatil = models.CharField(max_length=50, null=True, blank=True)
    
    fec_irreparable = models.DateField(null=True, blank=True)
    fec_inoperativo = models.DateField(null=True, blank=True)
    ns = models.CharField(max_length=50, null=True, blank=True)
    codigo_equipo = models.CharField(max_length=50, null=True, blank=True)
    cardex_revisado = models.BooleanField(default=False, null=True, blank=True)
    area_general = models.CharField(max_length=100, null=True, blank=True, verbose_name="Área General/Propietaria")

    def __str__(self):  
        return f"{self.nomDisp} ({self.num_serie})"

class Inventario(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    id_trabajador = models.ForeignKey(Empleado, on_delete=models.CASCADE, verbose_name="Trabajador que registra")
    ubiImv = models.CharField(max_length=25, verbose_name="Ubicación de Almacenamiento", null=True, blank=True)
    cantIngreso = models.PositiveIntegerField(verbose_name="Cantidad de Componentes")
    
    # CORREGIDO: Añadimos paréntesis y lo hacemos opcional
    fecEntregaCeneris = models.DateField(null=True, blank=True, verbose_name="Fecha de Entrega")
    
    descripInv = models.CharField(max_length=255, verbose_name="Descripción General del Lote", null=True, blank=True)
    
    # CORREGIDO: Añadimos paréntesis, max_length y lo hacemos opcional
    comentInv = models.CharField(max_length=500, null=True, blank=True, verbose_name="Comentarios Adicionales") 
                    
    tipInv = models.CharField(max_length=50, verbose_name="Tipo de Inventario", null=True, blank=True)
    estadInv = models.CharField(
        max_length=50,
        choices=[('Entrada','Entrada'), ('Salida','Salida')],
        verbose_name="Estado (Ingreso/Egreso)", null=True, blank=True
    )

    def __str__(self):
        return f"Inventario {self.id_inventario} - {self.descripInv[:50]}"

# cenerisapp/models.py

class Componente(models.Model):
    # --- CAMPOS COMUNES A TODOS LOS COMPONENTES ---
    id_componente = models.AutoField(primary_key=True)
    inventario = models.ForeignKey(
        Inventario, 
        on_delete=models.CASCADE, 
        related_name='componentes',
        null=True,  # Permite valores NULL en la base de datos
        blank=True  # Permite que el campo esté vacío en los formularios
    )
    nomComp = models.CharField(max_length=100, verbose_name="Nombre del Componente")
    descripComp = models.TextField(blank=True, verbose_name="Descripción / Comentario", null=True)
    nSerieActual = models.CharField(
        max_length=50, 
        unique=True, 
        null=True,  # Permite NULL en la base de datos
        blank=True, # Permite que el campo esté vacío en los formularios
        verbose_name="Número de Serie Actual"
    )

    def __str__(self):
        # Actualizamos para que se vea bien si no tiene N/S
        if self.nSerieActual:
            return f"{self.nomComp} ({self.nSerieActual})"
        return f"{self.nomComp} (ID: {self.id_componente}, sin N/S)"

    # Opcional: Añadir validación para asegurar que si hay un N/S, sea único
    def clean(self):
        super().clean()
        if self.nSerieActual: # Si se proporciona un número de serie
            # Buscamos si ya existe otro componente con el mismo N/S
            qs = Componente.objects.filter(nSerieActual=self.nSerieActual)
            # Excluimos el objeto actual si ya existe (para el caso de edición)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'nSerieActual': 'Ya existe un componente con este número de serie.'})

class Sensor(Componente):
    # --- CAMPOS ESPECÍFICOS PARA SENSORES ---
    dispositivo_instalado = models.ForeignKey(
        Dispositivo, 
        on_delete=models.SET_NULL, # Si se borra el dispositivo, el sensor no se borra, solo se desasigna.
        null=True, 
        blank=True,
        verbose_name="Instalado en Dispositivo"
    )
    estComp = models.CharField(max_length=50, blank=True, verbose_name="Estado (Operativo/No)",null=True)
    fecFabComp = models.DateField(null=True, blank=True, verbose_name="Fecha de Fabricación")
    fecInst = models.DateField(null=True, blank=True, verbose_name="Fecha de Instalación")
    fecVencGarantia = models.DateField(null=True, blank=True, verbose_name="Vencimiento de Garantía")
    tipGas = models.CharField(max_length=30, null=True, blank=True, verbose_name="Tipo de Gas")
    nro_guia_ingreso = models.CharField(max_length=50, null=True, blank=True) # Nombre de la BD
    entregCeneris = models.BooleanField(default=False, verbose_name="¿Entregado a Ceneris?")
    item_guia = models.CharField(max_length=50, null=True, blank=True)
    info_canibalizado = models.CharField(max_length=255, blank=True, verbose_name="Info Sensor Canibalizado", null=True)

    @property
    def enUso(self):
        return self.dispositivo_instalado is not None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class OtroComponente(Componente):
    ESTADO_CHOICES = [
        ('Operativo', 'Operativo (En Stock)'),
        ('Prestado', 'Prestado'),
        ('Inoperativo', 'Inoperativo'),
        ('Extraviado', 'Extraviado'),
    ]
    tipGas = models.CharField(max_length=30, blank=True, verbose_name="Tipo de Gas")
    estComp = models.CharField(max_length=50, blank=True, verbose_name="Estado",choices=ESTADO_CHOICES, default='Operativo')
    fecFabComp = models.DateField(null=True, blank=True)
    entregCeneris = models.BooleanField(default=False, verbose_name="¿Entregado a Ceneris?")

class Programa(models.Model):
    MES_CHOICES = [
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ]
    TIPO_DISPOSITIVO_CHOICES = [
        ('Fijo', 'Dispositivos Fijos'),
        ('Portatil', 'Dispositivos Portátiles'),
    ]
    
    id_programa = models.AutoField(primary_key=True)
    
    # --- CAMPOS NUEVOS Y MEJORADOS ---
    ano = models.IntegerField(verbose_name="Año")
    mes = models.IntegerField(choices=MES_CHOICES, verbose_name="Mes")
    tipo_dispositivo = models.CharField(
        max_length=20,
        choices=TIPO_DISPOSITIVO_CHOICES,
        verbose_name="Tipo de Dispositivo"
    )

    # fecInicio = models.DateField(verbose_name="Fecha de Inicio") <-- Se elimina
    # fecFin = models.DateField(verbose_name="Fecha de Fin")     <-- Se elimina
    
    totalPrograma = models.IntegerField(verbose_name="Total Programado")
    totalEjecutado = models.IntegerField(default=0, verbose_name="Total Ejecutado")
    comentarios = models.TextField(blank=True)

    def __str__(self):
        # Usamos 'get_mes_display' para obtener el nombre del mes
        return f"Programa {self.get_tipo_dispositivo_display()} - {self.get_mes_display()} {self.ano}"

    @property
    def porcentaje_progreso(self):
        if self.totalPrograma is None or self.totalPrograma == 0:
            return 0
        progreso = (self.totalEjecutado / self.totalPrograma) * 100
        return min(int(progreso), 100)
        
    class Meta:
        # Ordenamos por año y mes, los más recientes primero
        ordering = ['-ano', '-mes']
        # Evitamos que se pueda crear el mismo programa dos veces (ej. "Agosto 2025 - Fijos")
        unique_together = ('ano', 'mes', 'tipo_dispositivo')


class Certificado(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='certificados')
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    id_programa = models.ForeignKey(Programa, on_delete=models.CASCADE, blank=True, null=True)
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE, null=True, blank=True, related_name='certificados_de_componente')
    estado_inicial = models.CharField(max_length=50, blank=True)
    estadoFinal = models.CharField(max_length=50)
    fechCertificado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Certificado")
    proxFecha = models.DateField()
    temp = models.CharField(max_length=50)
    presion = models.CharField(max_length=50)
    humedadRelativa = models.CharField(max_length=50)
    rango_medicion = models.CharField(max_length=50)
    nro_certificado = models.CharField(max_length=50, default='00000', unique=True)

    def __str__(self):
        return self.estadoFinal
    
    class Meta:
        # Le dice a Django que siempre que pidas certificados,
        # los devuelva ordenados por fecha, del más reciente al más antiguo.
        ordering = ['-fechCertificado']

class PatronesCalibracion(models.Model):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE)
    numPatron = models.CharField(max_length=50, null=True, blank=True)
    patronUtil = models.CharField(max_length=30)
    n_p = models.CharField(max_length=30)
    n_lote = models.CharField(max_length=30)
    n_certificado = models.CharField(max_length=40)
    fechaExpiracion = models.DateField()

    def __str__(self):
        return self.numPatron
    
class Resultados(models.Model):
    id_resultado = models.AutoField(primary_key=True)
    id_certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE)
    gas = models.CharField(max_length=50)  # <-- Agrega este campo si quieres guardar el gas
    lecturaPatron = models.CharField(max_length=50)
    lecturaEquipo = models.CharField(max_length=50)
    prob_error = models.CharField(max_length=50)

    def __str__(self):
        return f"Resultados {self.id_resultado}"

class Parte(models.Model):

    id_parte = models.AutoField(primary_key=True)
    # Relación clave: Cada parte pertenece a un único dispositivo
    id_dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='partes')
    
    nomPart = models.CharField(
        max_length=100,
        verbose_name="Nombre de la Parte"
    )
    estado = models.CharField(
        max_length=50,
        default='Operativo',
        verbose_name="Estado"
    )

    fecFab = models.DateField(null=True, blank=True, verbose_name="Fecha de Fabricación")

    def __str__(self):
        return f"{self.nomPart} de {self.id_dispositivo.nomDisp}"

    class Meta:
        # Restricción para que no se pueda añadir la misma parte dos veces al mismo dispositivo
        unique_together = ('id_dispositivo', 'nomPart')

class Modificacion(models.Model):
    id_modificacion = models.AutoField(primary_key=True)
    id_dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, verbose_name="Dispositivo Afectado")
    
    # --- LA CORRECCIÓN CLAVE ---
    parte_saliente = models.ForeignKey(Parte, on_delete=models.SET_NULL, null=True, blank=True, related_name='reparaciones_salida')
    sensor_saliente = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True, blank=True, related_name='reparaciones_salida')

    # Guardamos una referencia al ítem nuevo que se puso (el reemplazo)
    componente_entrante = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True, blank=True, related_name='reparaciones_entrada')
    
    id_trabajador = models.ForeignKey(Empleado, on_delete=models.CASCADE, verbose_name="Realizado por")
    MotivoCambio = models.CharField(max_length=255, verbose_name="Motivo del Servicio")
    fecInstalacionMod = models.DateField(verbose_name="Fecha de Modificación")
    tipoServicio = models.CharField(max_length=50, choices=[ ('Reparacion', 'Reparación')])
    descrTrabajo = models.TextField(verbose_name="Descripción del Trabajo")

    

    class Meta:
        # Le dice a Django que el orden por defecto para este modelo es la fecha descendente
        ordering = ['-fecInstalacionMod']

    def __str__(self):
        return self.MotivoCambio

    def clean(self):
        # Validación para asegurar que solo uno de los dos (sensor o parte) se elija.
        if self.parte_saliente and self.sensor_saliente:
            raise ValidationError("Una reparación solo puede afectar a una parte O a un sensor, no a ambos.")

class Alarma(models.Model):
    id_alarma = models.AutoField(primary_key=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='alarmas')
    primera = models.CharField(max_length=50)
    segunda = models.CharField(max_length=50)
    tercera = models.CharField(max_length=50)
    und = models.CharField(max_length=50)
    equipo = models.CharField(max_length=50)
    cilindro = models.CharField(max_length=50)
    def __str__(self):
        return f"Alarma para {self.sensor}"


class Reporte (models.Model):
    id_reporte = models.AutoField ( primary_key=True)
    id_dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Dispositivo Afectado")
    id_otro_componente = models.ForeignKey(OtroComponente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Componente Afectado (Bomba/Acople)")
    id_trabajador = models.ForeignKey ( Empleado, on_delete=models.CASCADE, null=True, blank=True)
    fecReport = models.DateField(null=True, blank=True)
    razRetiro = models.CharField(max_length=255)
    especRetiro = models.CharField(max_length=255)
    def clean(self):
        # Validación para asegurar que se elija un dispositivo O un componente, pero no ambos.
        if self.id_dispositivo and self.id_otro_componente:
            raise ValidationError("Un reporte solo puede estar asociado a un Dispositivo O a un Componente, no a ambos.")
            
    def save(self, *args, **kwargs):
        self.full_clean() # Llama al método clean() antes de guardar
        super().save(*args, **kwargs)


class Registro(models.Model):
    id_registro = models.AutoField(primary_key=True)
    trabajador_receptor = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='registros_recibidos',
        verbose_name="Trabajador que recibe el equipo"
    )
    
    
    operador_responsable = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE,
        related_name='registros_realizados',
        verbose_name="Operador que registra"
    )
    id_dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    area_trabajo_operacion = models.ForeignKey(
        AreaTrabajo, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Área de la Operación"
    )
    punto_exacto_operacion = models.ForeignKey(
        PuntoExacto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Punto Exacto de la Operación"
    )

    id_componente = models.ForeignKey(Componente, on_delete=models.CASCADE, null=True, blank=True)

    fecRegistro = models.DateTimeField(auto_now_add=True) 
    fecDevol = models.DateTimeField(null=True, blank=True) # ¡CLAVE! Puede estar vacío
    durPrestamo = models.DurationField(null=True, blank=True) # ¡CLAVE! Puede estar vacío
    turno = models.CharField(max_length=10, blank=True, choices=[('A', 'A'), ('B', 'B')])

    def clean(self):
        if self.id_dispositivo_id and self.id_componente_id:
            raise ValidationError("Un registro solo puede estar asociado a un dispositivo O a un componente, no a ambos.")

        if not self.id_dispositivo_id and not self.id_componente_id:
            raise ValidationError("El registro debe estar asociado a un dispositivo o a un componente.")


class Calibracion(models.Model):
    ESTADO_CHOICES = [
        ('Calibrado', 'Calibrado'),
        ('No Calibrado', 'No Calibrado'),
    ]
    id_calibracion = models.AutoField(primary_key=True)
    id_dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    fecCalibracionC = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=255, choices=ESTADO_CHOICES, default='No Calibrado')

    def __str__(self):
        return f"Calibración para {self.id_dispositivo}: {self.estado}"

class Ventas(models.Model):
    id_ventas = models.AutoField(primary_key=True)
    id_componente = models.ForeignKey(Componente, on_delete=models.SET_NULL, null=True)
    fecVenta = models.DateField()
    estado = models.CharField(max_length=255)

    def __str__(self):
        return f"Venta {self.id_ventas}"    

class Mantenimiento(models.Model):
    id_mantenimiento = models.AutoField(primary_key=True)
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='mantenimientos')
    tecnico_a_cargo = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_intervencion = models.DateTimeField(auto_now_add=True)
    estado_inicial_equipo = models.CharField(max_length=50, null=True, blank=True)
    estado_final_equipo = models.CharField(max_length=50, null=True, blank=True)
    
    # ¡LA MAGIA! JSONField para guardar el estado de todas las partes
    # Guardará algo como: 
    # {"Carcasa delantera y filtros": "Bueno", "Pernos Carcasa": "Regular", "Sensor O2": "Cambiado", ...}
    checklist_partes = models.JSONField(default=dict)
    
    componentes_mal_estado = models.TextField(blank=True, verbose_name="Componentes en Mal Estado", null=True)
    componentes_estado_regular = models.TextField(blank=True, verbose_name="Componentes en Estado Regular", null=True)
    cambios_realizados = models.TextField(blank=True, verbose_name="Cambios Realizados")

    
    observacion_msa = models.TextField(blank=True, verbose_name="Observación (MSA)")
    
    def __str__(self):
        return f"Mantenimiento para {self.dispositivo} el {self.fecha_intervencion.strftime('%d/%m/%Y')}"

    class Meta:
        ordering = ['-fecha_intervencion']


class FotoDispositivo(models.Model):
    # Relación: cada foto pertenece a un dispositivo
    CONTEXTO_CHOICES = [
        ('REPORTE_VISUAL', 'Reporte Visual (Fijos)'),
        ('MANTENIMIENTO', 'Reporte de Mantenimiento'),
        ('CARDEX', 'Reporte CARDEX'),
        ('GENERAL', 'General'),
    ]
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='fotos')
    
    
    # Campo para la imagen. Se guardará en la carpeta 'media/dispositivo_fotos/'
    imagen_original = models.ImageField(
        upload_to='dispositivo_fotos/originales/',
        verbose_name="Imagen Original"
    )
    
    thumbnail = ImageSpecField(
        source='imagen_original',
        processors=[ResizeToFill(400, 300)],
        format='JPEG',
        options={'quality': 85}
    )
    
    # Tipo de foto: para saber si es la 'EVIDENCIA', 'SENSOR_O2', etc.
    # Es un campo de texto simple para máxima flexibilidad.
    tipo_foto = models.CharField(max_length=50, verbose_name="Tipo de Evidencia")
    
    # --- ¡NUEVO CAMPO DE CONTEXTO! ---
    contexto = models.CharField(
        max_length=50,
        choices=CONTEXTO_CHOICES,
        default='GENERAL',
        verbose_name="Pertenece a"
    )

    fecha_carga = models.DateTimeField(auto_now_add=True)

    modificacion = models.ForeignKey(
        Modificacion, 
        on_delete=models.SET_NULL, # Si se borra la modificación, la foto no se borra.
        null=True, 
        blank=True,               # Es opcional, una foto puede ser general.
        related_name='fotos',
        verbose_name="Modificación Asociada"
    )

    def __str__(self):
        return f"Foto de {self.tipo_foto} para {self.dispositivo.nomDisp}"

class InformeCalibracion(models.Model):
    id_informe = models.AutoField(primary_key=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='informes_calibracion')
    
    informe = models.TextField(verbose_name="Informe", null=True, blank=True)
    encontrado_calibracion = models.TextField(verbose_name="Encontrado", null=True, blank=True)
   
    sensor_cambiado = models.TextField(verbose_name="¿Se cambió el sensor?", null=True, blank=True)
    
    fecha_informe = models.DateField(verbose_name="Fecha del Informe", null=True, blank=True)
    
    
    empresa_realizadora = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Realizada por")

    observacion = models.TextField(verbose_name="Observación",null=True, blank=True)

    def __str__(self):
        return f"Informe para {self.sensor} el {self.fecha_informe}"

    class Meta:
        ordering = ['-fecha_informe']

class SeguimientoDiario(models.Model):
    id_seguimiento = models.AutoField(primary_key=True)
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    fecha = models.DateField()
    
    # Usaremos un CharField para guardar el símbolo/texto exacto del estado
    estado_texto = models.CharField(max_length=50, verbose_name="Estado del Día")
    
    class Meta:
        # Asegura que solo haya un registro por dispositivo por día
        unique_together = ('dispositivo', 'fecha')
        ordering = ['fecha']

class ObservacionDispositivo(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='observaciones')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    comentario = models.TextField(verbose_name="Comentario")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Observación para {self.dispositivo.nomDisp} el {self.fecha_creacion.strftime('%d/%m/%Y')}"

    class Meta:
        ordering = ['-fecha_creacion']

class Ocurrencia(models.Model):
    id_ocurrencia = models.AutoField(primary_key=True)
    # Relacionamos la ocurrencia con el usuario de Django que la creó.
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    # El contenido del mensaje
    mensaje = models.TextField(verbose_name="Mensaje de la Ocurrencia")
    pci = models.CharField(max_length=100, verbose_name="PCI Asociado", null=True, blank=True)
    # La fecha y hora se guardan automáticamente al crear el registro
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Mostramos el autor y una parte del mensaje
        autor_nombre = self.autor.username if self.autor else "Usuario Anónimo"
        return f"Ocurrencia de {autor_nombre} el {self.fecha_creacion.strftime('%d/%m/%Y')}"

    class Meta:
        # Ordenamos las ocurrencias de la más reciente a la más antigua
        ordering = ['-fecha_creacion']

def ruta_archivo_reporte(instance, filename):
    # Genera una ruta de guardado organizada: media/reportes_diarios/TIPO/AÑO/MES/archivo.pdf
    return f"reportes_diarios/{instance.tipo_reporte}/{instance.fecha.year}/{instance.fecha.month}/{filename}"

class ReporteDiario(models.Model):
    # Usamos un CharField para definir los 3 tipos de reportes que necesitas.
    TIPO_CHOICES = [
        ('ALARM', 'Reporte de Alarmas'),
        ('GALAXY', 'Reporte Diario Galaxy'),
        ('QUINCENAL', 'Informe Quincenal'),
    ]

    tipo_reporte = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateField(verbose_name="Fecha del Reporte")
    archivo = models.FileField(upload_to=ruta_archivo_reporte, verbose_name="Archivo del Reporte")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Aseguramos que solo haya un archivo por día para cada tipo de reporte
        unique_together = ('tipo_reporte', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_reporte_display()} - {self.fecha.strftime('%d/%m/%Y')}"

class DatosPDF(models.Model):
    # Relación OneToOne: cada certificado tiene un único conjunto de datos PDF
    certificado = models.OneToOneField(Certificado, on_delete=models.CASCADE, primary_key=True,related_name='datos_pdf')
    
    # Campos que antes estaban en el formulario
    num_paginas_pdf = models.PositiveIntegerField(null=True,blank=True)
    codigo_pdf = models.CharField(max_length=100, blank=True, null=True)
    version_pdf = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Datos PDF para Certificado #{self.certificado.nro_certificado}"

def ruta_anexo_certificado(instance, filename):
    # Genera una ruta organizada: media/certificados_anexos/CERT_ID/nombre_archivo.jpg
    _, extension = os.path.splitext(filename)
    return f"certificados_anexos/{instance.certificado.pk}/anexo_{instance.pk or 'new'}{extension}"

class AnexoCertificado(models.Model):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='anexos')
    imagen = models.ImageField(upload_to=ruta_anexo_certificado, verbose_name="Imagen del Anexo")
    # Opcional: puedes añadir un campo de descripción por si quieres ponerle un título a cada anexo
    # descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Anexo para Certificado #{self.certificado.nro_certificado}"