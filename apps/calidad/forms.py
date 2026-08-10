# calidad/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import (
    Clinica, ArchivoClinica, EMO, Control
)
import datetime
from recursoshumanos.models import (
    Empresa, Proyecto, Cargo, Trabajador
)


# ======================================================
# FORMULARIOS PARA GESTIÓN DE EMOs
# ======================================================

class ProgramarEmoForm(forms.ModelForm):
    comentario_alerta = forms.CharField(
        label="Comentario (solo para correo)",
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Escribe una nota para el trabajador (solo se enviará por correo)...'
            }
        )
    )

    # Campos "virtuales" para la lógica de proyectos
    proyecto_padre = forms.ModelChoiceField(
        queryset=Proyecto.objects.filter(parent__isnull=True, activo=True),
        label="Proyecto Padre",
        required=False, 
        empty_label="Seleccionar Proyecto Principal (Opcional)"
    )
    subproyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.none(), 
        label="Subproyecto / Área",
        required=False,
        empty_label="Seleccionar Subproyecto (si aplica)"
    )
    
    # Campo de empresa para seleccionar la empresa del EMO
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all().order_by('nombre'),
        label="Empresa",
        required=False,
        empty_label="Seleccionar Empresa (Opcional)"
    )

    class Meta:
        model = EMO
        # Asegúrate de que 'cargo' está en esta lista
        fields = ['trabajador', 'empresa', 'tipo_emo', 'cargo', 'lugar_examen', 'fecha_programada', 'hora_examen']
        widgets = {
            'fecha_programada': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'hora_examen': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        hoy = datetime.date.today()
        trabajadores_notificables_qs = Trabajador.objects.filter(
            activo=True
        ).filter(
            Q(fecha_cese__isnull=True) | Q(fecha_cese__gt=hoy)
        ).order_by('apellido_paterno', 'apellido_materno', 'nombres')

        # En edición, permitimos mantener el trabajador actual aunque esté cesado,
        # para no romper registros históricos.
        if self.instance.pk and self.instance.trabajador_id:
            trabajadores_notificables_qs = (trabajadores_notificables_qs | Trabajador.objects.filter(pk=self.instance.trabajador_id)).distinct()

        self.fields['trabajador'].queryset = trabajadores_notificables_qs
        
        # Placeholders
        self.fields['trabajador'].empty_label = "Seleccionar Trabajador *"
        self.fields['lugar_examen'].empty_label = "Seleccionar Clínica (Opcional)"
        self.fields['empresa'].empty_label = "Seleccionar Empresa *"
        
        # --- CARGO ---
        # Aseguramos que el cargo tenga un placeholder claro
        self.fields['cargo'].empty_label = "Seleccionar Cargo para este EMO *"
        # Si quieres que sea OBLIGATORIO seleccionar un cargo, descomenta la siguiente línea:
        # self.fields['cargo'].required = True 

        # Tipo EMO
        tipo_emo_choices = list(EMO.TIPO_EMO_CHOICES)
        self.fields['tipo_emo'].choices = [('', 'Seleccionar Tipo de EMO *')] + tipo_emo_choices

        # Fecha obligatoria
        self.fields['fecha_programada'].required = True
        self.fields['fecha_programada'].label = "Fecha a realizar EMO *"
        
        # --- EMPRESA ---
        # Si se está editando un EMO existente, pre-cargamos su empresa
        if self.instance.pk and self.instance.empresa:
            self.initial['empresa'] = self.instance.empresa.id

        # Lógica de carga dinámica de subproyectos (igual que antes)
        if 'proyecto_padre' in self.data:
            try:
                padre_id_raw = self.data.get('proyecto_padre')
                if padre_id_raw:
                    padre_id = int(padre_id_raw)
                    self.fields['subproyecto'].queryset = Proyecto.objects.filter(parent_id=padre_id, activo=True)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            # Corregir lógica de carga: modelo usa 'proyecto' para padre y 'subproyecto' para hijo
            if self.instance.proyecto:
                self.initial['proyecto_padre'] = self.instance.proyecto.id
                self.fields['subproyecto'].queryset = Proyecto.objects.filter(
                    parent_id=self.instance.proyecto.id, activo=True
                )
            
            if self.instance.subproyecto:
                self.initial['subproyecto'] = self.instance.subproyecto.id

    def save(self, commit=True):
        # 1. Creamos la instancia con los datos básicos del formulario (incluido el cargo)
        instance = super().save(commit=False)
        
        # 2. Lógica manual para PROYECTOS
        padre = self.cleaned_data.get('proyecto_padre')
        sub = self.cleaned_data.get('subproyecto')

        if sub:
            instance.proyecto = sub.parent  # El proyecto es el padre
            instance.subproyecto = sub      # El subproyecto es el hijo
        elif padre:
            instance.proyecto = padre
            instance.subproyecto = None
        else:
            instance.proyecto = None
            instance.subproyecto = None

        # 3. Lógica para EMPRESA
        # Capturamos la empresa seleccionada del formulario
        empresa_seleccionada = self.cleaned_data.get('empresa')
        if empresa_seleccionada:
            instance.empresa = empresa_seleccionada
        else:
            # Si no se selecciona empresa, usamos la empresa por defecto del trabajador
            instance.empresa = instance.trabajador.empresa

        # 4. REFUERZO DE SEGURIDAD PARA EL CARGO
        # Leemos explícitamente el cargo de los datos limpios y lo asignamos
        cargo_seleccionado = self.cleaned_data.get('cargo')
        if cargo_seleccionado:
            instance.cargo = cargo_seleccionado

        if commit:
            instance.save()
        return instance
    
    def clean_trabajador(self):
        trabajador = self.cleaned_data.get('trabajador')
        proyecto = self.cleaned_data.get('proyecto_padre') or self.cleaned_data.get('subproyecto')

        if trabajador:
            hoy = datetime.date.today()
            if (not trabajador.activo) or (trabajador.fecha_cese and trabajador.fecha_cese <= hoy):
                raise ValidationError("No se puede programar ni notificar EMO a un trabajador cesado/inactivo.")
        
        # Un trabajador puede tener múltiples EMOs, pero solo uno por proyecto
        if not self.instance.pk:  # Si es un EMO nuevo (no edición)
            # Buscar si ya existe un EMO para este trabajador + proyecto
            if proyecto:
                if EMO.objects.filter(
                    trabajador=trabajador,
                    proyecto=proyecto.parent if self.cleaned_data.get('subproyecto') else proyecto,
                    estado='Programado'
                ).exists():
                    raise ValidationError(f"Este trabajador ya tiene un EMO programado para el proyecto '{proyecto.nombre}'.")
            # Si no hay proyecto seleccionado, permitir crear EMO
        return trabajador

class RegistrarResultadoEmoForm(forms.ModelForm):
    """
    Formulario multi-paso para registrar o editar el resultado de un EMO.
    """
    cantidad_controles = forms.IntegerField(
        label="Cantidad de Controles de Seguimiento",
        required=False,
        min_value=0,
        max_value=10,
        widget=forms.NumberInput(attrs={'id': 'id_cantidad_controles'})
    )
    
    eliminar_archivo_pdf = forms.BooleanField(
        required=False,
        label="Eliminar resultado actual",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = EMO
        fields = [
            'fecha_realizacion', 'aptitud', 'fecha_vencimiento',
            'restriccion', 'comentario', 'archivo_pdf'
        ]
        widgets = {
            'fecha_realizacion': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
            'restriccion': forms.Textarea(attrs={'rows': 4}),
            'comentario': forms.Textarea(attrs={'rows': 4}),
            # Usamos FileInput simple para evitar que Django renderice "Actualmente: ..." y el checkbox "Limpiar" por defecto
            'archivo_pdf': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'fecha_realizacion': 'Fecha de Realización del EMO',
            'aptitud': 'Resultado de Aptitud Médica',
            'fecha_vencimiento': 'Fecha de Vencimiento del EMO',
            'restriccion': 'Restricción (Si aplica)',
            'comentario': 'Observación / Comentario Adicional',
            'archivo_pdf': 'PDF del Resultado del EMO',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacemos que el campo de archivo PDF no sea obligatorio
        self.fields['archivo_pdf'].required = False

        # Asignamos clases CSS para todos los campos del formulario
        self.fields['fecha_realizacion'].widget.attrs['class'] = 'form-control'
        self.fields['aptitud'].widget.attrs['class'] = 'form-control'
        self.fields['fecha_vencimiento'].widget.attrs['class'] = 'form-control'
        self.fields['restriccion'].widget.attrs['class'] = 'form-control'
        self.fields['comentario'].widget.attrs['class'] = 'form-control'
        self.fields['archivo_pdf'].widget.attrs['class'] = 'form-control'
        self.fields['cantidad_controles'].widget.attrs['class'] = 'form-control'
        
        # ============================================= #
        #        ¡LA SOLUCIÓN DEFINITIVA ESTÁ AQUÍ!     #
        # ============================================= #
        # Forzamos el formato que el widget HTML 'type="date"' espera (YYYY-MM-DD).
        # Esto anula cualquier formato de fecha localizado que Django intente usar.
        self.fields['fecha_realizacion'].widget.format = '%Y-%m-%d'
        self.fields['fecha_vencimiento'].widget.format = '%Y-%m-%d'

class SubsanacionEmoForm(forms.ModelForm):
    """
    Formulario para subir el archivo de subsanación.
    """
    class Meta:
        model = EMO
        # Solo necesitamos este campo del usuario.
        fields = ['archivo_subsana']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que el campo sea obligatorio en el formulario.
        self.fields['archivo_subsana'].required = True
        self.fields['archivo_subsana'].label = "Archivo de Subsanación (PDF)"

class ConfirmacionLecturaForm(forms.ModelForm):
    # 1. Definimos el campo explícitamente para desactivar la localización automática
    fecha_confirmacion = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d', # Le decimos al widget: "Escribe la fecha así"
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'], # Aceptamos ambos formatos al recibir
        localize=False, # ¡CLAVE! Evita que Django lo convierta a DD/MM/AAAA
        label='Fecha de Lectura'
    )
    
    eliminar_archivo = forms.BooleanField(
        required=False,
        label="Eliminar archivo actual",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = EMO
        fields = ['fecha_confirmacion', 'archivo_confirmacion']
        widgets = {
            'archivo_confirmacion': forms.FileInput(attrs={
                'class': 'form-control file-input-standard'
            }),
        }
        labels = {
            'archivo_confirmacion': 'PDF de la Lectura Firmada'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Obligatoriedad
        self.fields['archivo_confirmacion'].required = False
        self.fields['archivo_confirmacion'].widget.attrs.pop('required', None)

        # 2. REFUERZO: Forzar el valor en el atributo HTML value
        # Esto es necesario si Django sigue intentando localizar el dato a pesar de todo.
        if self.instance and self.instance.pk and self.instance.fecha_confirmacion:
            fecha_val = self.instance.fecha_confirmacion
            
            # Obtener string YYYY-MM-DD
            if isinstance(fecha_val, datetime.datetime):
                fecha_str = fecha_val.date().isoformat()
            elif isinstance(fecha_val, str):
                fecha_str = fecha_val[:10]
            else:
                fecha_str = fecha_val.strftime('%Y-%m-%d')

            # Inyectar directamente en el HTML
            self.fields['fecha_confirmacion'].widget.attrs['value'] = fecha_str

class ControlForm(forms.ModelForm):
    class Meta:
        model = Control
        fields = ['fecha_programada', 'descripcion']

# ======================================================
# FORMULARIOS PARA CONFIGURACIÓN (Empresas, Proyectos, etc.)
# ======================================================

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre', 'ruc', 'direccion', 'telefono', 'email_contacto', 'persona_contacto']
    
    def clean_ruc(self):
        # ... (tu validación de RUC se queda igual)
        pass



class ClinicaForm(forms.ModelForm):
    class Meta:
        model = Clinica
        fields = ['nombre', 'direccion', 'imagen_fachada', 'telefono', 'email_contacto', 'persona_contacto', 'google_maps_url']
        widgets = {
            'imagen_fachada': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'google_maps_url': forms.URLInput(attrs={
                'placeholder': 'https://maps.google.com/maps?...',
                'class': 'form-control'
            }),
        }

class ArchivoClinicaForm(forms.ModelForm):
    class Meta:
        model = ArchivoClinica
        fields = ['descripcion', 'archivo_pdf', 'activo']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Ej: Speech para procedimiento de medición',
                'class': 'form-control'
            }),
            'archivo_pdf': forms.FileInput(attrs={
                'accept': '.pdf,.doc,.docx,.txt',
                'class': 'form-control',
                'required': True
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ['codigo', 'nombre', 'descripcion']
        widgets = {
            'codigo': forms.TextInput(attrs={'placeholder': 'Ej: TEC-01 (Opcional)'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Técnico de Mantenimiento Eléctrico'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción de las funciones del cargo (opcional)'}),
        }

class RegistrarControlForm(forms.ModelForm):
    """
    Formulario específico para subir el archivo de evidencia de un control ya existente.
    """
    class Meta:
        model = Control
        # El único campo que el usuario debe proporcionar en esta pantalla es el archivo.
        fields = ['archivo_adjunto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que el campo de archivo sea obligatorio para esta acción.
        self.fields['archivo_adjunto'].required = True
        self.fields['archivo_adjunto'].label = "Archivo de Evidencia (PDF)"