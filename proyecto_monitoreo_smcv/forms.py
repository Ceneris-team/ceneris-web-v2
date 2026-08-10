from django import forms
from django.forms import ClearableFileInput, inlineformset_factory
from .models import Trabajador, Puesto, Agente, Cargo, Diagnostico, Mantenimiento, Operatividad, Calibracion, Accesorio, HistorialCambioAccesorio, Dispositivo, Inspeccion, DetalleInspeccion, PruebaTecnica, InspeccionPatron, EquipoReportado, FilaCronograma, Ubicacion
from .models import Trabajador, Puesto, Agente, Cargo, Diagnostico, Mantenimiento, GerenciaGeneral, Gerencia, Superintendencia

# Clase base para darle estilo Tailwind a todos los inputs
class TailwindBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Estilo estándar para inputs de texto, selects, etc.
            field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm py-2 px-3 border'

class TrabajadorForm(TailwindBaseForm):
    class Meta:
        model = Trabajador
        fields = ['nombre', 'ap_paterno', 'ap_materno', 'dni', 'cargo', 'telefono', 'correo']
        # Etiquetas personalizadas si las necesitas
        labels = {
            'ap_paterno': 'Apellido Paterno',
            'ap_materno': 'Apellido Materno',
            'dni': 'DNI / Identificación',
        }

class CargoForm(TailwindBaseForm):
    class Meta:
        model = Cargo
        fields = ['nombre']

class AgenteForm(TailwindBaseForm):
    class Meta:
        model = Agente
        fields = ['nombre']
        labels = {'nombre': 'Nombre del Agente de Riesgo'}

# Formulario para Ubicación
class UbicacionForm(TailwindBaseForm):
    class Meta:
        model = Ubicacion
        fields = ['nombre', 'descripcion']
        labels = {
            'nombre': 'Nombre de la Ubicación',
            'descripcion': 'Descripción (opcional)',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm py-2 px-3 border',
                'rows': 3,
                'placeholder': 'Ej. Área de trabajo en el piso 2, sector norte...',
            }),
        }

# Formulario para Puesto
class PuestoForm(TailwindBaseForm):
    class Meta:
        model = Puesto
        fields = ['nombre', 'superintendencia']
        labels = {'nombre': 'Nombre del Puesto', 'superintendencia': 'Superintendencia Asociada'}

# Formulario para Gerencia General
class GerenciaGeneralForm(TailwindBaseForm):
    class Meta:
        model = GerenciaGeneral
        fields = ['nombre']
        labels = {'nombre': 'Nombre de la Gerencia General'}

# Formulario para Gerencia
class GerenciaForm(TailwindBaseForm):
    class Meta:
        model = Gerencia
        fields = ['gerencia_general', 'nombre']
        labels = {
            'gerencia_general': 'Gerencia General (Padre)',
            'nombre': 'Nombre de la Gerencia'
        }

# Formulario para Superintendencia
class SuperintendenciaForm(TailwindBaseForm):
    class Meta:
        model = Superintendencia
        fields = ['gerencia', 'nombre']
        labels = {
            'gerencia': 'Pertenece a la Gerencia',
            'nombre': 'Nombre de la Superintendencia'
        }

# Formulario para subida de excel
class CargaMasivaPlanForm(forms.Form):
    archivo_excel = forms.FileField(
        label="Archivo Excel (.xlsx)",
        help_text="Columnas requeridas: Gerencia, Superintendencia, Puesto, Agente, Cantidad"
    )
    mes = forms.IntegerField(min_value=1, max_value=12, label="Mes de Programación")
    anio = forms.IntegerField(min_value=2024, max_value=2030, label="Año", initial=2025)

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class DiagnosticoForm(forms.ModelForm):
    descripcion_fotos = forms.CharField(
        label="Descripción / Nota para las fotos",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700',
            'placeholder': 'Ej. Vista frontal y daños laterales'
        })
    )

    class Meta:
        model = Diagnostico
        fields = '__all__'
        widgets = {
            # Buscador para dispositivo (Le ponemos una clase especial 'select2-enable')
            'dispositivo': forms.Select(attrs={
                'class': 'tom-select-enable w-full' 
            }),
            # Campos de texto y select normales (arreglamos visibilidad)
            'estado': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700 placeholder-gray-400',
                'placeholder': 'Ej. En revisión'
            }),
            'numero': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700 placeholder-gray-400',
                'placeholder': 'Ej. DIAG-001'
            }),
            # Corrección del error de fecha (yyyy-MM-dd)
            'fecha_recepcion': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}
            ),
            'fecha_manufactura': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}
            ),
            'fecha_revision': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),

            'diagnostico': forms.Textarea(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 
                'rows': 3
            }),
            'recomendaciones': forms.Textarea(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 
                'rows': 3
            }),
        }

class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = '__all__'
        widgets = {
            # Buscador Tom Select
            'dispositivo': forms.Select(attrs={'class': 'tom-select-enable w-full'}),
            
            # Selects normales con estilo Tailwind
            'cliente': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'proveedor': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            
            # Inputs de texto
            'equipo_contraste': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'estado_final': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 'placeholder': 'Ej. Operativo'}),
            
            # Textarea
            'trabajo': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 'rows': 4}),
        }

class OperatividadForm(forms.ModelForm):
    class Meta:
        model = Operatividad
        fields = ['dispositivo', 'estado_inicial', 'estado_final', 'fecha_recepcion', 'fecha_operatividad']
        widgets = {
            'dispositivo': forms.Select(attrs={'class': 'tom-select-enable w-full'}),
            'estado_inicial': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white', 'placeholder': 'Ej. Regular / Malo'}),
            'estado_final': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white', 'placeholder': 'Ej. Operativo / Bueno'}),
            'fecha_recepcion': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white'}),
            'fecha_operatividad': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white'}),
        }

class CalibracionForm(forms.ModelForm):
    class Meta:
        model = Calibracion
        fields = ['dispositivo', 'estado_inicial', 'estado_final', 'fecha_recepcion', 'fecha_calibracion']
        widgets = {
            'dispositivo': forms.Select(attrs={'class': 'tom-select-enable w-full'}),
            'estado_inicial': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'estado_final': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'fecha_recepcion': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border rounded'}),
            'fecha_calibracion': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border rounded'}),
        }

class HistorialCambioAccesorioForm(forms.ModelForm):
    accesorio = forms.ModelChoiceField(
        queryset=Accesorio.objects.filter(dispositivo__nombre__icontains='Vibrometro'),
        widget=forms.Select(attrs={
            'class': 'tom-select-enable w-full' 
        }),
        label="Accesorio (Vibrómetro)"
    )

    class Meta:
        model = HistorialCambioAccesorio
        fields = ['accesorio', 'fecha_cambio', 'proximo_cambio', 'observacion']
        widgets = {
            'fecha_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'proximo_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'observacion': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 'rows': 2}),
        }

class CambioDosimetroForm(forms.ModelForm):
    accesorio = forms.ModelChoiceField(
        queryset=Accesorio.objects.filter(dispositivo__nombre__icontains='Dosimetro'),
        widget=forms.Select(attrs={'class': 'tom-select-enable w-full'}),
        label="Accesorio (Dosímetro)"
    )

    class Meta:
        model = HistorialCambioAccesorio
        fields = ['accesorio', 'fecha_cambio', 'proximo_cambio', 'observacion']
        widgets = {
            'fecha_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'proximo_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'observacion': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 'rows': 2}),
        }

class CambioBombaForm(forms.ModelForm):
    accesorio = forms.ModelChoiceField(
        queryset=Accesorio.objects.filter(dispositivo__nombre__icontains='Bomba'),
        widget=forms.Select(attrs={'class': 'tom-select-enable w-full'}),
        label="Accesorio (Bomba)"
    )

    class Meta:
        model = HistorialCambioAccesorio
        fields = ['accesorio', 'fecha_cambio', 'proximo_cambio', 'observacion']
        widgets = {
            'fecha_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'proximo_cambio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700'}),
            'observacion': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded bg-white text-gray-700', 'rows': 2}),
        }

class InspeccionEspecificaForm(forms.Form):
    # --- 1. CABECERA ---
    fecha_inspeccion = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border rounded'}),
        label="Fecha de Inspección"
    )
    responsable = forms.ModelChoiceField(
        queryset=Trabajador.objects.all(),
        widget=forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
        label="Responsable"
    )
    
    # --- 2. EQUIPO A INSPECCIONAR ---
    dispositivo = forms.ModelChoiceField(
        queryset=Dispositivo.objects.all().order_by('nombre'),
        widget=forms.Select(attrs={'class': 'tom-select-enable w-full', 'id': 'select-dispositivo'}),
        label="Seleccione el Equipo"
    )

    # --- 3. ESTADO DEL EQUIPO (Checklist) ---
    # Usamos RadioButtons para simular el check único (Bueno/Malo/NA)
    OPCIONES_ESTADO = [('B', 'Bueno'), ('M', 'Malo'), ('NA', 'No Aplica')]
    
    estado_case = forms.ChoiceField(choices=OPCIONES_ESTADO, widget=forms.RadioSelect, initial='B')
    estado_botones = forms.ChoiceField(choices=OPCIONES_ESTADO, widget=forms.RadioSelect, initial='B')
    estado_pantalla = forms.ChoiceField(choices=OPCIONES_ESTADO, widget=forms.RadioSelect, initial='B')
    estado_bateria = forms.ChoiceField(choices=OPCIONES_ESTADO, widget=forms.RadioSelect, initial='B')
    estado_accesorios = forms.ChoiceField(choices=OPCIONES_ESTADO, widget=forms.RadioSelect, initial='B')
    
    # --- AGREGAR A SECCIÓN BOMBA ---
    bomba_flujo_constante = forms.ChoiceField(
        choices=[('SI', 'SI'), ('NO', 'NO')], 
        widget=forms.RadioSelect, initial='SI', required=False
    )
    bomba_ruido_excesivo = forms.ChoiceField(
        choices=[('SI', 'SI'), ('NO', 'NO')], 
        widget=forms.RadioSelect, initial='NO', required=False
    )
    observaciones_generales = forms.CharField(
        required=False, 
        label="Observaciones Generales del Estado",
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'w-full p-2 border border-gray-300 rounded mt-1',
            'placeholder': 'Ej. Ninguna / Desgaste leve en carcasa...'
        })
    )
    # --- AGREGAR A SECCIÓN VIBROMETRO ---
    vibro_aeq_x = forms.CharField(required=False, label="Eje X - AEQ(m/s2)")
    vibro_aeq_y = forms.CharField(required=False, label="Eje Y - AEQ(m/s2)")
    vibro_aeq_z = forms.CharField(required=False, label="Eje Z - AEQ(m/s2)")

    observaciones_estado = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'w-full border rounded'}))

    # --- 4. PRUEBA DE OPERATIVIDAD (Común) ---
    hora_inicio = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'p-2 border rounded'}), required=False)
    hora_fin = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'p-2 border rounded'}), required=False)
    tiempo_total = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Ej: 07h 44min', 'class': 'p-2 border rounded'}))
    
    # --- 5. CAMPOS ESPECÍFICOS (Se muestran/ocultan con JS) ---
    
    # A. BOMBA GRAVIMÉTRICA
    flujo_evaluacion = forms.CharField(required=False, label="Flujo Evaluación")
    flujo_pre = forms.DecimalField(required=False, max_digits=6, decimal_places=3, label="Pre-Calibración (L/m)")
    flujo_post = forms.DecimalField(required=False, max_digits=6, decimal_places=3, label="Post-Calibración (L/m)")
    flujo_promedio = forms.DecimalField(required=False, max_digits=6, decimal_places=3, label="Promedio (L/m)")
    bomba_flujo_constante = forms.ChoiceField(choices=[('SI', 'SI'), ('NO', 'NO')], required=False, initial='SI')
    bomba_ruido_excesivo = forms.ChoiceField(choices=[('SI', 'SI'), ('NO', 'NO')], required=False, initial='NO')

    # B. DOSÍMETRO DE RUIDO
    tasa_cambio = forms.CharField(required=False, initial="3 dB")
    ponderacion = forms.CharField(required=False, initial="A")
    respuesta = forms.CharField(required=False, initial="Slow/Baja")
    db_pre = forms.DecimalField(required=False, max_digits=6, decimal_places=2, label="Pre-Calibración dB(A)")
    db_post = forms.DecimalField(required=False, max_digits=6, decimal_places=2, label="Post-Calibración dB(A)")
    lectura_max = forms.DecimalField(required=False, label="L. máx dB")
    lectura_min = forms.DecimalField(required=False, label="L. min dB")
    lectura_pico = forms.DecimalField(required=False, label="L. pico dB")
    fuentes_ruido = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    # C. VIBRÓMETRO
    serie_cuerpo = forms.CharField(required=False, label="Serie (C. Completo)")
    sens_x_cuerpo = forms.CharField(required=False, label="Eje X")
    sens_y_cuerpo = forms.CharField(required=False, label="Eje Y")
    sens_z_cuerpo = forms.CharField(required=False, label="Eje Z")

    # Mano Brazo
    serie_mano = forms.CharField(required=False, label="Serie (Mano Brazo)")
    sens_x_mano = forms.CharField(required=False, label="Eje X")
    sens_y_mano = forms.CharField(required=False, label="Eje Y")
    sens_z_mano = forms.CharField(required=False, label="Eje Z")
    aeq_x = forms.CharField(required=False, label="Nivel AEQ X")
    aeq_y = forms.CharField(required=False, label="Nivel AEQ Y")
    aeq_z = forms.CharField(required=False, label="Nivel AEQ Z")

    # PATRÓN (Común para todos)
    equipo_patron = forms.ModelChoiceField(
        queryset=Dispositivo.objects.all(), # Aquí podrías filtrar solo calibradores
        required=False,
        widget=forms.Select(attrs={'class': 'tom-select-enable w-full'}),
        label="Equipo Patrón Utilizado"
    )

    observaciones_finales = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'w-full border rounded'}))
    resultado_final = forms.CharField(initial="Equipo operativo.", widget=forms.TextInput(attrs={'class': 'w-full border rounded'}))


class InspeccionConjuntaForm(forms.ModelForm):
    class Meta:
        model = Inspeccion
        fields = [
            'fecha_inspeccion', 'responsable', 
            'total_equipos', 'equipos_en_campo', 'cant_muestra',
            # Campos checklist
            'dosi_operatividad', 'dosi_limpieza', 'dosi_accesorios', 'dosi_obs',
            'bomba_operatividad', 'bomba_limpieza', 'bomba_accesorios', 'bomba_obs',
            'vibro_operatividad', 'vibro_limpieza', 'vibro_accesorios', 'vibro_obs',
        ]
        widgets = {
            'fecha_inspeccion': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all shadow-sm'
            }),
            'responsable': forms.Select(attrs={
                'class': 'w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white shadow-sm'
            }),
            'total_equipos': forms.NumberInput(attrs={
                'class': 'w-full pl-10 pr-3 py-2 border border-blue-200 bg-blue-50 text-blue-800 font-bold rounded-lg cursor-not-allowed shadow-inner',
                'readonly': 'readonly'
            }),
            'equipos_en_campo': forms.NumberInput(attrs={
                'class': 'w-full pl-8 pr-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 outline-none transition-all'
            }),
            'cant_muestra': forms.NumberInput(attrs={
                'class': 'w-full pl-8 pr-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none transition-all'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lista de campos que quieres que sean opcionales (permitan '-')
        campos_opcionales = [
            'responsable',
            'dosi_operatividad', 'dosi_limpieza', 'dosi_accesorios',
            'bomba_operatividad', 'bomba_limpieza', 'bomba_accesorios',
            'vibro_operatividad', 'vibro_limpieza', 'vibro_accesorios'
        ]
        
        for campo in campos_opcionales:
            self.fields[campo].required = False

# Formulario para cada fila de la Muestra (Detalle)
class DetalleMuestraForm(forms.ModelForm):
    # Campos extra que no están en DetalleInspeccion pero sí en la tabla visual
    # Usaremos PruebaTecnica para guardar los valores numéricos
    pre_calibracion = forms.DecimalField(
        required=False, 
        max_digits=10, 
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'w-20 border p-1 text-center', 
            'placeholder': '0.000',
            'step': '0.001' # Permite decimales en el navegador
        })
    )
    post_calibracion = forms.DecimalField(
        required=False, 
        max_digits=10, 
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'w-20 border p-1 text-center', 
            'placeholder': '0.000',
            'step': '0.001'
        })
    )
    
    no_aplica = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4'}))

    equipo_patron = forms.ModelChoiceField(
        queryset=Dispositivo.objects.all(), # Podrías filtrar .filter(uso='Patron') si tienes ese campo
        required=False,
        widget=forms.Select(attrs={'class': 'tom-select-enable w-32'}), # Estrecho para la tabla
        label="Patrón"
    )
    
    class Meta:
        model = DetalleInspeccion
        fields = ['dispositivo', 'resultado_final'] # Y los campos virtuales arriba
        widgets = {
            'dispositivo': forms.Select(attrs={'class': 'tom-select-enable w-80'}),
        }

# El Formset Mágico
DetalleMuestraFormSet = inlineformset_factory(
    Inspeccion, DetalleInspeccion, 
    form=DetalleMuestraForm,
    extra=2, # Muestra 5 filas vacías por defecto
    can_delete=True
)

class InspeccionPatronForm(forms.ModelForm):
    class Meta:
        model = InspeccionPatron
        fields = ['patron', 'observacion']
        widgets = {
            'patron': forms.Select(attrs={'class': 'tom-select-enable w-80'}),
            'observacion': forms.TextInput(attrs={'class': 'w-full border p-1'}),
        }

class EquipoReportadoForm(forms.ModelForm):
    # Redefinimos los campos para hacerlos opcionales y evitar el bloqueo
    fecha_reporte = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'border p-1 w-32'})
    )
    motivo = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'w-full border p-1'})
    )
    estado = forms.CharField(
        required=False, 
        initial="Inoperativo",
        widget=forms.TextInput(attrs={'class': 'w-24 border p-1'})
    )

    class Meta:
        model = EquipoReportado
        fields = ['dispositivo', 'fecha_reporte', 'motivo', 'estado']
        widgets = {
            # Hacemos el select también opcional a nivel de widget/form
            'dispositivo': forms.Select(attrs={'class': 'tom-select-enable w-80'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aseguramos que el dispositivo no sea obligatorio
        self.fields['dispositivo'].required = False

PatronFormSet = inlineformset_factory(Inspeccion, InspeccionPatron, form=InspeccionPatronForm, extra=1, can_delete=True)
ReportadoFormSet = inlineformset_factory(Inspeccion, EquipoReportado, form=EquipoReportadoForm, extra=1, can_delete=True)

class FilaCronogramaForm(forms.ModelForm):
    # Selectores múltiples para equipos
    equipos_programados = forms.ModelMultipleChoiceField(
        queryset=Dispositivo.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'tom-select-enable w-full'}),
        required=False
    )
    equipos_ejecutados = forms.ModelMultipleChoiceField(
        queryset=Dispositivo.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'tom-select-enable w-full'}),
        required=False,
        label="Equipos Realmente Ejecutados (Dejar vacío si es igual a programado)"
    )

    class Meta:
        model = FilaCronograma
        fields = ['numero', 'fecha_programada', 'ejecutado', 'equipos_programados', 'equipos_ejecutados', 'observaciones']
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'type': 'date', 'class': 'border p-2 rounded w-full'}),
            'ejecutado': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
            'numero': forms.NumberInput(attrs={'class': 'border p-2 rounded w-20'}),
            'observaciones': forms.Textarea(attrs={'class': 'border p-2 rounded w-full', 'rows': 3}),
        }