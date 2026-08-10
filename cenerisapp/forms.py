from django import forms
from django.forms import inlineformset_factory
from .models import Registro, Empleado, Dispositivo, Inventario, Sensor, OtroComponente, Alarma, Reporte, Calibracion, Ventas, Componente, Modificacion, Parte, Correo, Telefono, AreaTrabajo, Certificado,PatronesCalibracion, Resultados, Programa, Mantenimiento, FotoDispositivo, PuntoExacto, InformeCalibracion, SeguimientoDiario, Empresa, Ocurrencia, AnexoCertificado
from datetime import date


class RegistroSalidaForm(forms.ModelForm): # Un nuevo nombre para más claridad
    item_a_prestar = forms.ChoiceField(label="Dispositivo o Bomba a Prestar", required=True)

    class Meta:
        model = Registro
        fields = [
            'operador_responsable', 'trabajador_receptor', 
            'turno', 'area_trabajo_operacion', 'punto_exacto_operacion'
        ]
        labels = {
            'operador_responsable': 'Trabajador responsable',
            'turno': 'Turno',
        }
    def __init__(self, *args, **kwargs):
        # Primero, llamamos al __init__ del padre para que el formulario se construya
        super().__init__(*args, **kwargs)
        
        self.fields['operador_responsable'].queryset = Empleado.objects.filter(puesto__iexact="Supervisor")
        opciones = [('', '-----------')]
        
        # 1. Obtenemos los dispositivos portátiles
        dispositivos = Dispositivo.objects.filter(tipoDisp='Portatil')
        opciones.extend([(f'dispositivo_{d.pk}', str(d)) for d in dispositivos])
        
        # 2. Obtenemos los componentes "Bomba" disponibles
        bombas = Componente.objects.filter(
            nomComp__icontains='bomba', # Búsqueda insensible a mayúsculas
             otrocomponente__estComp='Operativo',
            sensor__isnull=True, # Asegura que es OtroComponente
            # (Añade aquí un filtro de estado si es necesario)
        )
        opciones.extend([(f'componente_{c.pk}', str(c)) for c in bombas])
        
        self.fields['item_a_prestar'].choices = opciones
    def clean_item_a_prestar(self):
        """
        Este método de validación se ejecuta para el campo 'item_a_prestar'.
        Lo usaremos para asignar el valor correcto a la instancia del modelo.
        """
        seleccion = self.cleaned_data.get('item_a_prestar')
        if not seleccion:
            # Si no se seleccionó nada, Django ya habrá lanzado un error de 'required'
            return None

        try:
            tipo, pk = seleccion.split('_')
            pk = int(pk)

            if tipo == 'dispositivo':
                # Asignamos el ID al campo del modelo en la instancia
                self.instance.id_dispositivo_id = pk
                self.instance.id_componente_id = None
            elif tipo == 'componente':
                # Asignamos el ID al campo del modelo en la instancia
                self.instance.id_componente_id = pk
                self.instance.id_dispositivo_id = None
            else:
                raise forms.ValidationError("Selección inválida.")
        
        except (ValueError, IndexError):
            raise forms.ValidationError("Formato de selección inválido.")
        
        return seleccion # Siempre devolvemos el valor original del campo al final

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        # Lista de campos que aparecerán en el formulario
        fields = [
            'id_trabajador', 
            'descripInv', 
            'ubiImv', 
            'tipInv', 
            'cantIngreso',
            'fecEntregaCeneris', 
            'comentInv'
        ]
        
        # Widgets para usar el selector de fecha del navegador
        widgets = {
            'fecEntregaCeneris': forms.DateInput(attrs={'type': 'date'}),
            'comentInv': forms.Textarea(attrs={'rows': 3}), # Hace el campo de comentarios más grande
        }

class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        # La lista 'fields' ahora incluye TODOS los campos que el usuario debe poder editar,
        # tanto los del modelo Sensor como los de su padre Componente.
        fields = [
            
            'nSerieActual',
            'descripComp',
            
            # Campos del modelo hijo 'Sensor'
            'dispositivo_instalado',
            'estComp',
            'fecFabComp',
            'fecInst',
            'fecVencGarantia',
            'tipGas',
            'nro_guia_ingreso',
            'entregCeneris',
            'item_guia',
        ]
        
        # Widgets para mejorar la apariencia
        widgets = {
            'fecFabComp': forms.DateInput(attrs={'type': 'date'}),
            'fecInst': forms.DateInput(attrs={'type': 'date'}),
            'fecVencGarantia': forms.DateInput(attrs={'type': 'date'}),
            'descripComp': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que el campo de dispositivo no sea obligatorio
        if 'dispositivo_instalado' in self.fields:
             self.fields['dispositivo_instalado'].required = False

class SensorLoteForm(forms.ModelForm):
    class Meta:
        model = Sensor
        # Incluimos solo los campos relevantes para un ingreso nuevo
        fields = [
            'descripComp',
            'fecFabComp',

            'fecVencGarantia',
            'tipGas',
            'nro_guia_ingreso',
            'entregCeneris',
            'item_guia',
        ]
        widgets = {
            'fecFabComp': forms.DateInput(attrs={'type': 'date'}),
            'fecVencGarantia': forms.DateInput(attrs={'type': 'date'}),
            'descripComp': forms.Textarea(attrs={'rows': 2}),
        }


class OtroComponenteForm(forms.ModelForm):
    class Meta:
        model = OtroComponente
        fields = [
            'nSerieActual', 'estComp', 'tipGas',
            'entregCeneris', 'descripComp'
        ]
        widgets = {
            'descripComp': forms.Textarea(attrs={'rows': 2}),
        }


class DispositivoForm(forms.ModelForm):
    cantidad_sensores = forms.IntegerField(
        label="Cantidad de Sensores a Asignar", 
        min_value=0, 
        initial=1,
        required=False # No es obligatorio para guardar el dispositivo
    )
    class Meta:
        model = Dispositivo
        # Incluye todos los campos que quieres en el formulario principal
        fields = [
            'nomDisp', 'num_serie', 'tag', 'tipoDisp', 'id_areaTrabajo_fijo','area_general','ns',
            'marca', 'fabDisp', 'fecVencimientoGarantia',   
            'fecFabricacion', 'id_empresa'
        ]
        labels = {
            'nomDisp': 'Nombre del Dispositivo',
            'num_serie': 'Número de Serie',
            'tag': 'Tag',
            'tipoDisp': 'Tipo de Dispositivo',
            'ns': 'Número de Servicio (N/S)',
            'fabDisp': 'Fabricante',
            'fecVencimientoGarantia': 'Fecha de Vencimiento de Garantía',
            'fecFabricacion': 'Fecha de Fabricación',
        }

        widgets = {
            'fecVencimientoGarantia': forms.DateInput(attrs={'type': 'date'}),
            'fecFabricacion': forms.DateInput(attrs={'type': 'date'}),
        }

class SensorParaDispositivoForm(forms.ModelForm):
    class Meta:
        model = Sensor
        # Excluimos los campos que se llenarán automáticamente
        fields = [
            'nomComp', 'nSerieActual', 'estComp', 'tipGas', 'fecFabComp', 
            'fecInst', 'fecVencGarantia', 'nro_guia_ingreso',
            'descripComp'
        ]
        widgets = {
            'fecFabComp': forms.DateInput(attrs={'type': 'date'}),
            'fecInst': forms.DateInput(attrs={'type': 'date'}),
            'fecVencGarantia': forms.DateInput(attrs={'type': 'date'}),
            'descripComp': forms.Textarea(attrs={'rows': 2}),
        }

class BaseSensorParaDispositivoFormSet(forms.BaseFormSet):
    def clean(self):
        """
        Valida que no haya sensores con el mismo nombre y N/S 
        dentro de los formularios de este lote.
        """
        if any(self.errors):
            # No hagas nada si los formularios individuales ya tienen errores
            return
        
        super().clean() # Llama a la limpieza del padre primero

        nombres_vistos = set()
        series_vistas = set()
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            if form.cleaned_data:
                nombre = form.cleaned_data.get('nomComp')
                n_serie = form.cleaned_data.get('nSerieActual')
                
                # Validar nombre duplicado en el lote
                if nombre and nombre in nombres_vistos:
                    raise forms.ValidationError(f"El nombre de componente '{nombre}' está repetido en este formulario.")
                if nombre:
                    nombres_vistos.add(nombre)

                # Validar N/S duplicado en el lote
                if n_serie and n_serie in series_vistas:
                    raise forms.ValidationError(f"El Número de Serie '{n_serie}' está repetido en este formulario.")
                if n_serie:
                    series_vistas.add(n_serie)

class AlarmaFijoForm(forms.ModelForm):
    """Formulario para crear un registro completo de Alarma para un dispositivo Fijo."""
    class Meta:
        model = Alarma
        # Excluimos id_dispositivo porque lo asignaremos en la vista
        exclude = ('id_dispositivo',)
        labels = {
            'primera': 'Primera Alarma',
            'segunda': 'Segunda Alarma',
            'tercera': 'Tercera Alarma',
            'und': 'Unidad de Medida',
            'equipo': 'Equipo Asociado',
            'cilindro': 'Cilindro de Gas',
        }

class AlarmaPortatilForm(forms.ModelForm):
    """Formulario para actualizar solo el campo de alarma de un dispositivo Portátil."""
    class Meta:
        model = Dispositivo
        # Solo queremos editar este campo
        fields = ['alarmaPortatil']
        labels = {
            'alarmaPortatil': 'Nivel de Alarma Portátil',
        }

class ReporteForm(forms.ModelForm):
    TIPO_REPORTE_CHOICES = [
        ('', '-----------'),
        ('dispositivo', 'Reportar un Dispositivo'),
        ('componente', 'Reportar un Componente (Bomba/Acople)'),
    ]
    tipo_reporte = forms.ChoiceField(choices=TIPO_REPORTE_CHOICES, required=True, label="¿Qué deseas reportar?")

    NUEVO_ESTADO_CHOICES = [
        ('Inoperativo', 'Marcar como Inoperativo'),
        ('Extraviado', 'Marcar como Extraviado'),
    ]
    nuevo_estado = forms.ChoiceField(
        choices=NUEVO_ESTADO_CHOICES,
        required=True,
        label="Acción a tomar / Nuevo estado"
    )

    class Meta:
        model = Reporte
        # Especificamos los campos que el usuario debe llenar
        fields = [
            'id_dispositivo','id_otro_componente',
            'id_trabajador',
            'razRetiro',
            'especRetiro'
        ]
        
        # Etiquetas más amigables en español
        labels = {
            'id_dispositivo': 'Dispositivo Afectado',
            'id_otro_componente': 'Componente Afectado (Bomba/Acople)',
            'id_trabajador': 'Reportado por',
            'fecReport': 'Fecha del Reporte',
            'razRetiro': 'Razón del Retiro / Daño',
            'especRetiro': 'Especificaciones / Detalles del Daño',
        }
        
        # Widgets para mejorar la interfaz
        widgets = {
            'fecReport': forms.DateInput(attrs={'type': 'date'}),
            'razRetiro': forms.Textarea(attrs={'rows': 3}),
            'especRetiro': forms.Textarea(attrs={'rows': 4}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que los campos no sean requeridos a nivel de HTML,
        # ya que el JS y la validación 'clean' se encargarán de la lógica.
        self.fields['id_dispositivo'].required = False
        self.fields['id_otro_componente'].required = False
        
        # Filtramos el queryset para que solo muestre 'Bomba' y 'Acople de Bomba'
        self.fields['id_otro_componente'].queryset = OtroComponente.objects.filter(
            nomComp__in=['Bomba', 'Acople de Bomba']
        )
    def clean(self):
        cleaned_data = super().clean()
        
        tipo = cleaned_data.get('tipo_reporte')
        dispositivo = cleaned_data.get('id_dispositivo')
        componente = cleaned_data.get('id_otro_componente')
        
        if tipo == 'dispositivo':
            if not dispositivo:
                self.add_error('id_dispositivo', 'Debes seleccionar un dispositivo.')
            # Limpiamos el otro campo para asegurar la consistencia
            cleaned_data['id_otro_componente'] = None
        
        elif tipo == 'componente':
            if not componente:
                self.add_error('id_otro_componente', 'Debes seleccionar un componente.')
            # Limpiamos el otro campo
            cleaned_data['id_dispositivo'] = None
            
        else:
            # Si no se seleccionó ni dispositivo ni componente en el primer dropdown
            self.add_error('tipo_reporte', 'Debes seleccionar qué tipo de item deseas reportar.')
            
        return cleaned_data

class CalibracionForm(forms.ModelForm):
    class Meta:
        model = Calibracion
        # Excluimos la PK que es autoincremental
        fields = ['id_dispositivo', 'fecCalibracionC', 'estado']
        
        labels = {
            'id_dispositivo': 'Dispositivo Calibrado',
            'fecCalibracionC': 'Fecha de Calibración',
            'estado': 'Estado de la Calibración',
        }
        
        widgets = {
            'fecCalibracionC': forms.DateInput(attrs={'type': 'date'}),
            'estado': forms.Textarea(attrs={'rows': 3}),
        }

class VentaForm(forms.ModelForm):
    componente_ns = forms.CharField(
        label="Buscar Componente por Número de Serie",
        help_text="Empieza a escribir para buscar componentes disponibles.",
        widget=forms.TextInput(attrs={'autocomplete': 'off'}) # Desactiva el autocompletado del navegador
    )
    id_componente = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = Ventas
        fields = ['fecVenta', 'estado'] # ¡IMPORTANTE! El orden aquí no importa
        labels = { 'fecVenta': 'Fecha de Venta', 'estado': 'Estado de la Venta' }
        widgets = { 'fecVenta': forms.DateInput(attrs={'type': 'date'}) }

    # --- ¡NUEVO MÉTODO DE VALIDACIÓN! ---
    def clean_id_componente(self):
        componente_id = self.cleaned_data.get('id_componente')
        
        if not componente_id:
            raise forms.ValidationError("Debes seleccionar un componente de la lista de sugerencias.")

        try:
            # Ahora Python sabrá qué es 'Componente'
            componente = Componente.objects.get(pk=componente_id)
            
            # Y también sabrá qué es 'Sensor' (si lo importas también)
            if hasattr(componente, 'sensor') and componente.sensor.dispositivo_instalado:
                raise forms.ValidationError(f"El sensor '{componente}' está instalado y no se puede vender.")
        
        # Y aquí también
        except Componente.DoesNotExist:
            raise forms.ValidationError("El componente seleccionado no existe o no es válido.")

        return componente_id

class ModificacionForm(forms.ModelForm):
    # Campo para seleccionar el ítem que se va a quitar. Se poblará en la vista.
    item_saliente = forms.ChoiceField(
        label="Componente o Parte Afectada",
        choices=[('', 'Primero selecciona un dispositivo')],
        required=True
    )
    

    # Campo oculto que guardará el ID del ítem de reemplazo
    reemplazo_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False
    )

    n_serie_reemplazo = forms.CharField(
        label="N° de Serie del Componente de Reemplazo",
        required=False, # Lo haremos requerido con JS y en la validación 'clean'
        max_length=50,
        help_text="Introduce el número de serie del nuevo componente que estás instalando."
    )

    class Meta:
        model = Modificacion
        # Campos del modelo que el usuario llena directamente
        fields = [
            'id_dispositivo',
            'id_trabajador',
            'MotivoCambio',
            'tipoServicio',
            'descrTrabajo'
        ]
        widgets = {
            'descrTrabajo': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        # Sacamos las opciones que le pasaremos desde la vista
        opciones_salientes = kwargs.pop('opciones_salientes', None)
        super().__init__(*args, **kwargs)

        # Si la vista nos pasó opciones, las usamos para llenar el select
        if opciones_salientes:
            self.fields['item_saliente'].choices = [('', '-----------')] + opciones_salientes

    def clean(self):
        cleaned_data = super().clean()
        
        # --- Lógica para 'item_saliente' (se queda igual) ---
        seleccion_saliente = cleaned_data.get("item_saliente")
        if seleccion_saliente:
            try:
                tipo, pk = seleccion_saliente.split('_')
                if tipo == 'sensor':
                    self.instance.sensor_saliente_id = pk
                    self.instance.parte_saliente_id = None
                elif tipo == 'parte':
                    self.instance.parte_saliente_id = pk
                    self.instance.sensor_saliente_id = None
            except (ValueError, IndexError):
                self.add_error('item_saliente', "Selección inválida.")

        # --- ¡NUEVA VALIDACIÓN PARA EL REEMPLAZO! ---
        tipo_servicio = cleaned_data.get("tipoServicio")
        reemplazo_id = cleaned_data.get("reemplazo_id")

        if tipo_servicio == 'Reparacion' and reemplazo_id:
            try:
                componente_reemplazo = Componente.objects.get(pk=reemplazo_id)
                
                # Comprobaciones
                is_available_and_operative = False
                if hasattr(componente_reemplazo, 'sensor'):
                    sensor = componente_reemplazo.sensor
                    if sensor.dispositivo_instalado is None and sensor.estComp == 'Operativo':
                        is_available_and_operative = True
                    else:
                        # --- LA CORRECCIÓN ---
                        # Usamos 'None' para el campo para que sea un error general
                        raise forms.ValidationError(
                            f"El sensor de reemplazo '{sensor}' no está disponible o no está operativo."
                        )
                elif hasattr(componente_reemplazo, 'otrocomponente'):
                    otro = componente_reemplazo.otrocomponente
                    if otro.estComp == 'Operativo':
                        is_available_and_operative = True
                    else:
                        raise forms.ValidationError(
                             f"El componente de reemplazo '{otro}' no está operativo."
                        )

                if is_available_and_operative:
                    self.instance.componente_entrante_id = reemplazo_id

            except Componente.DoesNotExist:
                # --- LA CORRECCIÓN ---
                raise forms.ValidationError(
                    "El componente de reemplazo seleccionado no existe."
                )
        reemplazo_id = cleaned_data.get("reemplazo_id")
        n_serie_reemplazo = cleaned_data.get("n_serie_reemplazo")

        # --- VALIDACIÓN ADICIONAL ---
        if reemplazo_id:
            # Si se ha seleccionado un reemplazo, el N/S es obligatorio
            if not n_serie_reemplazo:
                self.add_error('n_serie_reemplazo', 'Este campo es obligatorio cuando se instala un reemplazo.')
            else:
                # Verificamos que el N/S no esté ya en uso por OTRO componente
                if Componente.objects.exclude(pk=reemplazo_id).filter(nSerieActual=n_serie_reemplazo).exists():
                    self.add_error('n_serie_reemplazo', 'Este número de serie ya está en uso por otro componente.')

        return cleaned_data



class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        # Excluimos los campos que no queremos que el usuario llene aquí
        fields = ['nomEmpleado', 'puesto', 'dni', 'areaTrabajo', 'supervisor']
        labels = {
            'nomEmpleado': 'Nombre Completo',
            'areaTrabajo': 'Área de Trabajo',
        }


CorreoFormSet = inlineformset_factory(
    Empleado,
    Correo,
    fields=('direccion_correo',),
    extra=0, # Mantenemos 1 para CREAR
    min_num=1,
    validate_min=True,
    can_delete=True,
    widgets={
        'direccion_correo': forms.TextInput(attrs={'placeholder': 'ejemplo@correo.com'})
    }
)
# --- FORMSET DE TELÉFONOS MEJORADO ---
TelefonoFormSet = inlineformset_factory(
    Empleado,
    Telefono,
    fields=('numero',),
    extra=0,           # No mostramos ningún formulario de teléfono por defecto
    min_num=1,         # No es obligatorio añadir un teléfono
    can_delete=True,
    widgets={
        'numero': forms.TextInput(attrs={'placeholder': 'Ej: +51 987654321'})
    }
)

ParteFormSet = inlineformset_factory(
    Dispositivo,      # Modelo Padre
    Parte,            # Modelo Hijo
    fields=('nomPart', 'estado'), # Campos a mostrar
    extra=1,          # Cuántos formularios extra mostrar por defecto
    can_delete=True,     # Permitir al usuario marcar partes para borrar
)
    
class AreaTrabajoForm(forms.ModelForm):
    class Meta:
        model = AreaTrabajo
        #son los campos del models que se mostrara
        fields = ['nombreA', 'ubicacionA']
        labels = {
            'nombreA': 'Nombre del Área',
            'ubicacionA': 'Ubicación del Área',
        }
        widgets = {
            'ubicacionA': forms.TextInput(attrs={'class': 'form-control'}),
        }

PuntoExactoFormSet = inlineformset_factory(
    AreaTrabajo,
    PuntoExacto,
    fields=('nombre_punto',),
    extra=1,
    can_delete=True
)

class CertificadoForm(forms.ModelForm):
    # Campos extra que no están en el modelo, solo para el PDF
    version_pdf = forms.CharField(label="Versión del documento", initial="2.0", required=False)

    class Meta:
        model = Certificado
        # Lista de campos del modelo que queremos en el formulario
        fields = [
            'estadoFinal', 'id_programa',
            'proxFecha', 'temp', 'presion', 'humedadRelativa',
            'rango_medicion', 'nro_certificado'
        ]
        # Widgets para mejorar la apariencia y funcionalidad
        widgets = {
            'proxFecha': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # --- LÓGICA AÑADIDA ---
        # Hacemos que todos estos campos sean opcionales a nivel de formulario.
        # La vista los rellenará con los datos del lote.
        campos_lote = ['temp', 'presion', 'humedadRelativa', 'proxFecha', 'rango_medicion']
        for campo in campos_lote:
            if campo in self.fields:
                self.fields[campo].required = False

    

PatronesFormSet = inlineformset_factory(
    Certificado,
    PatronesCalibracion,
    fields=('patronUtil', 'n_p', 'n_lote', 'n_certificado', 'fechaExpiracion'),
    extra=1,
    can_delete=True,
    widgets={
        'fechaExpiracion': forms.DateInput(attrs={'type': 'date'}),
    }
)

ResultadosFormSet = inlineformset_factory(
    Certificado,
    Resultados,
    fields=('gas', 'lecturaPatron', 'lecturaEquipo', 'prob_error'),
    extra=1,
    can_delete=True
)

class ProgramaCreateForm(forms.ModelForm):
    # Añadimos un campo para el año con una lista desplegable
    ano = forms.IntegerField(
        initial=date.today().year,
        widget=forms.Select(choices=[(y, y) for y in range(date.today().year - 2, date.today().year + 3)])
    )
    class Meta:
        model = Programa
        fields = ['ano', 'mes', 'tipo_dispositivo', 'totalPrograma', 'comentarios']
        labels = {
            'ano': 'Año',
            'mes': 'Mes',
            'tipo_dispositivo': 'Tipo de Dispositivo',
            'totalPrograma': 'Total a Programar',
            'comentarios': 'Comentarios',
        }
        widgets = {
            'comentarios': forms.Textarea(attrs={'rows': 3}),
        }

class ProgramaUpdateForm(forms.ModelForm):
    class Meta:
        model = Programa
        fields = ['totalPrograma', 'totalEjecutado', 'comentarios']
        widgets = {
            'comentarios': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_totalEjecutado(self):
        # Validación extra: no permitir que el total ejecutado sea mayor que el total programado
        ejecutado = self.cleaned_data.get('totalEjecutado')
        programado = self.instance.totalPrograma
        if ejecutado > programado:
            raise forms.ValidationError(f"El total ejecutado ({ejecutado}) no puede ser mayor que el total programado ({programado}).")
        return ejecutado
    
class MantenimientoForm(forms.ModelForm):
    actualizar_fec_inoperativo = forms.DateField(
        label="Establecer Fecha como Inoperativo",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    actualizar_fec_irreparable = forms.DateField(
        label="Establecer Fecha como Irreparable",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = Mantenimiento
        # El formulario ahora solo maneja los campos principales.
        # El checklist se manejará directamente en la plantilla y la vista.
        fields = [
            'tecnico_a_cargo', 'estado_inicial_equipo', 'estado_final_equipo', 'observacion_msa',
            'componentes_mal_estado', 'componentes_estado_regular',
            'cambios_realizados'
        ]
        widgets = {
            # Widgets para hacer los campos de texto más grandes
            'componentes_mal_estado': forms.Textarea(attrs={'rows': 2}),
            'componentes_estado_regular': forms.Textarea(attrs={'rows': 2}),
            'cambios_realizados': forms.Textarea(attrs={'rows': 2}),
            
        }


class FotoDispositivoForm(forms.ModelForm):
    modificacion = forms.ModelChoiceField(
        queryset=Modificacion.objects.none(),
        required=False,
        label="Asociar a una Reparación/Modificación (Opcional)",
        widget=forms.Select(attrs={'class': 'form-select'}) # Agregado estilo bootstrap
    )   
    
    class Meta:
        model = FotoDispositivo
        fields = ['modificacion','imagen_original', 'tipo_foto', 'contexto']
        labels = {
            'imagen_original': 'Seleccionar archivo de imagen',
            'tipo_foto': 'Tipo de Evidencia (Ej: EVIDENCIA, O2, H2S)',
            'contexto': 'Añadir reporte'
        }
        widgets = {
            'contexto': forms.Select(attrs={'class': 'form-select'}),
            'tipo_foto': forms.TextInput(attrs={'class': 'form-control'}),
            'imagen_original': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        modificaciones_queryset = kwargs.pop('modificaciones_queryset', None)
        super().__init__(*args, **kwargs)
        
        if modificaciones_queryset is not None:
            # 1. NO filtramos por componente_entrante__isnull=False.
            #    Queremos ver TODO (Partes salientes, sensores salientes, etc.)
            self.fields['modificacion'].queryset = modificaciones_queryset
            
            # 2. Definimos una función robusta para el texto del desplegable
            def get_label(obj):
                fecha = obj.fecInstalacionMod.strftime('%d/%m/%Y')
                detalle = "Modificación"

                # CASO A: Entró un componente
                if obj.componente_entrante:
                    # ¿Es un Sensor?
                    if hasattr(obj.componente_entrante, 'sensor'):
                        gas = obj.componente_entrante.sensor.tipGas
                        ns = obj.componente_entrante.sensor.nSerieActual
                        detalle = f"SENSOR Nuevo: {gas} (N/S: {ns})"
                    # Entonces es una Parte / Kit
                    else:
                        nombre = obj.componente_entrante.nomComp
                        detalle = f"PARTE Nueva: {nombre}"

                # CASO B: Salió una parte (y no entró nada)
                elif obj.parte_saliente:
                    detalle = f"RETIRO PARTE: {obj.parte_saliente.nomPart}"

                # CASO C: Salió un sensor
                elif obj.sensor_saliente:
                    detalle = f"RETIRO SENSOR: {obj.sensor_saliente.tipGas}"

                return f"[{fecha}] {detalle} - {obj.MotivoCambio[:30]}..."

            # Asignamos la función al campo
            self.fields['modificacion'].label_from_instance = get_label

        self.fields['contexto'].required = False
        self.fields['tipo_foto'].required = False

class InformeCalibracionForm(forms.ModelForm):
    class Meta:
        model = InformeCalibracion
        fields = ['informe', 'encontrado_calibracion','sensor_cambiado', 'fecha_informe', 'empresa_realizadora', 'observacion']
        widgets = {
            'fecha_informe': forms.DateInput(attrs={'type': 'date'}),
            'informe': forms.Textarea(attrs={'rows': 1}),
            'encontrado_calibracion': forms.Textarea(attrs={'rows': 1}),
        }

class SeguimientoDiarioForm(forms.ModelForm):
    ESTADO_CHOICES = [
        ('', '---'),
        ('OK - MAESTRANZA', 'OK - MAESTRANZA'),
        ('OK❤️ - MAESTRANZA', 'OK❤️ - MAESTRANZA'),
        ('OK - SMCV', 'OK - SMCV'),
        ('OK❤️ - SMCV', 'OK❤️ - SMCV'),
        ('OK', 'OK'),
        ('OK❤️', 'OK❤️'),
        ('⚠❤️', '⚠❤️'),
        ('SIN AUDIO', 'SIN AUDIO'),
        ('MALOGRADO', 'MALOGRADO'),
    ]
    
    # Sobrescribimos el campo para usar nuestras opciones
    estado_texto = forms.ChoiceField(choices=ESTADO_CHOICES, required=False)

    class Meta:
        model = SeguimientoDiario
        fields = ['estado_texto']

PuntoExactoFormSet = inlineformset_factory(
    AreaTrabajo,
    PuntoExacto,
    fields=('nombre_punto',),
    extra=1,
    can_delete=True
)

class OcurrenciaForm(forms.ModelForm):
    class Meta:
        model = Ocurrencia
        # Solo necesitamos que el usuario rellene el mensaje
        fields = ['mensaje', 'pci']
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Escribe tu ocurrencia, noticia o comentario aquí...'
            })
        }
        labels = {
            'mensaje': '', # No mostramos la etiqueta, el placeholder es suficiente
            'pci': 'Inicio de PCI:'
        }

class EmpleadoRapidoForm(forms.Form):
    # Campo para buscar o crear la empresa
    empresa_nombre = forms.CharField(
        label="Empresa",
        max_length=100,
        required=True,
        help_text="Busca una empresa existente o escribe un nuevo nombre para crearla."
    )
    # Campo oculto para guardar el ID de la empresa si se selecciona una existente
    empresa_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    # Campos para el nuevo empleado
    nomEmpleado = forms.CharField(label="Nombre Completo del Empleado", max_length=100, required=True)
    dni = forms.CharField(label="DNI del Empleado", max_length=8, required=True)
    puesto = forms.CharField(label="Puesto del Empleado", max_length=100, required=True)

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if Empleado.objects.filter(dni=dni).exists():
            raise forms.ValidationError("Ya existe un empleado con este DNI.")
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe contener 8 dígitos numéricos.")
        return dni


class ModificacionAntiguaForm(forms.Form):
    # Lista de opciones para los sensores
    SENSOR_NOMBRE_CHOICES = [
        ('', '---------'), # Opción vacía
        ('LEL', 'LEL'),
        ('O2', 'O2'),
        ('DUAL', 'DUAL'),
        ('SO2', 'SO2'),
        ('CO2', 'CO2'),
        ('NH3', 'NH3'),
        ('CL2', 'CL2'),
        ('HCN', 'HCN'),
        ('PID', 'PID'),
    ]

    dispositivo = forms.ModelChoiceField(
        queryset=Dispositivo.objects.all(),
        label="Dispositivo"
    )
    fecInstalacionMod = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de la Modificación"
    )

    # --- DATOS DEL SENSOR SALIENTE (CAMBIO AQUÍ) ---
    sensor_saliente_ns = forms.CharField(
        label="N/S Sensor Saliente",
        max_length=50,
        help_text="El N° de Serie del sensor que se retiró."
    )
    # Convertido a ChoiceField
    sensor_saliente_nombre = forms.ChoiceField(
        choices=SENSOR_NOMBRE_CHOICES,
        label="Nombre Sensor Saliente",
        help_text="Ej: Sensor O2, LEL, etc."
    )

    # --- DATOS DEL SENSOR ENTRANTE (CAMBIO AQUÍ) ---
    sensor_entrante_ns = forms.CharField(
        label="N/S Sensor Entrante",
        max_length=50,
        help_text="El N° de Serie del sensor nuevo que se instaló."
    )
    # Convertido a ChoiceField
    sensor_entrante_nombre = forms.ChoiceField(
        choices=SENSOR_NOMBRE_CHOICES,
        label="Nombre Sensor Entrante"
    )

    # --- DATOS ADICIONALES (sin cambios) ---
    id_trabajador = forms.ModelChoiceField(
        queryset=Empleado.objects.all(),
        label="Realizado Por"
    )
    MotivoCambio = forms.CharField(
        label="Motivo del Cambio",
        max_length=255,
        initial="Registro de historial"
    )

    evidencia_foto = forms.ImageField(
        label="Foto de Evidencia",
        required=False, # Es opcional, por si no tienes foto de ese evento antiguo
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )

class AnexoCertificadoForm(forms.ModelForm):
    class Meta:
        model = AnexoCertificado
        fields = ['imagen']