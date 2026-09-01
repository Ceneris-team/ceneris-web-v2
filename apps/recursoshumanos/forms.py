# recursoshumanos/forms.py
import json
from django import forms
from .models import CentroCosto, Proyecto, Cargo, Empresa, Trabajador, Ubicacion, Area, Dispositivo

class ProyectoForm(forms.ModelForm):
    tipo_proyecto = forms.ChoiceField(
        choices=[('', '---------'), ('padre', 'Proyecto Principal'), ('subproyecto', 'Subproyecto')],
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = Proyecto
        fields = ['nombre', 'codigo', 'fecha_inicio', 'activo', 'parent', 'empresa']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'nombre': 'Descripcion del Proyecto/Subproyecto',
            'codigo': 'Código del Proyecto/Subproyecto',
            'parent': 'Proyecto Principal al que pertenece',
            'empresa': 'Empresa Propietaria',
        }

    def __init__(self, *args, **kwargs):
        is_editing_subproject = kwargs.pop('is_editing_subproject', False)
        super().__init__(*args, **kwargs)
        
        self.fields['nombre'].required = False
        self.fields['codigo'].required = False
        self.fields['parent'].required = False
        self.fields['empresa'].required = False

        self.fields['parent'].empty_label = "-- Seleccionar Proyecto Principal --"
        self.fields['parent'].queryset = Proyecto.objects.filter(parent__isnull=True, activo=True).exclude(pk=self.instance.pk)
        
        if is_editing_subproject:
            del self.fields['parent']
        
        self.fields['empresa'].empty_label = "-- Seleccionar Empresa --"

        if self.instance and self.instance.pk:
            self.initial['tipo_proyecto'] = 'subproyecto' if self.instance.parent else 'padre'

    def clean_nombre(self):
        """Valida que el nombre del proyecto padre sea único."""
        nombre = self.cleaned_data.get('nombre')
        # Esta validación solo aplica si estamos creando/editando un proyecto padre.
        # El método clean() se encargará de la lógica condicional.
        if nombre and Proyecto.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un proyecto con este nombre.")
        return nombre

    def clean_codigo(self):
        """Valida que el código del subproyecto sea único."""
        codigo = self.cleaned_data.get('codigo')
        # Similar a 'nombre', la lógica condicional está en clean().
        if codigo and Proyecto.objects.filter(codigo__iexact=codigo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un proyecto o subproyecto con este código.")
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        tipo_proyecto = self.cleaned_data.get('tipo_proyecto')

        if not tipo_proyecto and self.instance and self.instance.pk:
            tipo_proyecto = 'subproyecto' if self.instance.parent else 'padre'

        if tipo_proyecto == 'padre':
            if not cleaned_data.get('nombre'): self.add_error('nombre', 'El nombre es obligatorio.')
            if not cleaned_data.get('empresa'): self.add_error('empresa', 'Debes seleccionar una empresa.')
            if not cleaned_data.get('codigo'): self.add_error('codigo', 'El código es obligatorio.')

        elif tipo_proyecto == 'subproyecto':
            if not cleaned_data.get('codigo'): self.add_error('codigo', 'El código es obligatorio.')
            if not self.instance.pk and not cleaned_data.get('parent'):
                 self.add_error('parent', 'Debes seleccionar un proyecto principal.')
        
        return cleaned_data

class CentroCostoForm(forms.ModelForm):
    class Meta:
        model = CentroCosto
        fields = ['codigo', 'nombre']

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['codigo', 'nombre', 'descripcion'] # Agregamos 'codigo' al inicio
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: A-001'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Recursos Humanos'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# ======================================================
# FORMULARIO PARA TRABAJADOR (MULTI-STEP)
# ======================================================
class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = [
            'dni', 'apellido_paterno', 'apellido_materno', 'nombres',
            'email', 'telefono', 'sexo', 'fecha_nacimiento',
            'empresa', 'area', 'cargo', 'sede', 'modalidad_evaluacion', 'activo',
            'fecha_ingreso', 'fecha_cese'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_cese': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'cargo': forms.Select(attrs={'class': 'form-select form-control'}),
            # 2. Agregamos estilo de Bootstrap al select de Área, Empresa y Sede
            'area': forms.Select(attrs={'class': 'form-select form-control'}),
            'empresa': forms.Select(attrs={'class': 'form-select form-control'}),
            'sede': forms.Select(attrs={'class': 'form-select form-control'}),
            'modalidad_evaluacion': forms.Select(attrs={'class': 'form-select form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-select form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- LA SOLUCIÓN PARA FECHAS ---
        date_fields = ['fecha_nacimiento', 'fecha_ingreso', 'fecha_cese']
        for field_name in date_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.format = '%Y-%m-%d'
                self.fields[field_name].input_formats = ['%Y-%m-%d']

        # --- ESTILOS DE ERROR ---
        for field_name in self.errors:
            field = self.fields.get(field_name)
            if field:
                attrs = field.widget.attrs
                attrs['class'] = attrs.get('class', '') + ' is-invalid'

        # --- PLACEHOLDERS (Para campos de TEXTO) ---
        # Nota: 'area' y 'centro_costo' ya no necesitan placeholder aquí
        # porque 'area' es un Select y 'centro_costo' se eliminó.
        placeholders = {
            'dni': '70612345',
            'apellido_paterno': 'Ingrese su apellido paterno',
            'apellido_materno': 'Ingrese su apellido materno ',
            'nombres': 'Ingrese sus nombres ',
            'email': 'ejemplo@correo.com',
            'telefono': '993 123 456',
        }
        for field_name, placeholder in placeholders.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = placeholder
        
        # --- OBLIGATORIEDAD DE CAMPOS ---
        self.fields['fecha_nacimiento'].required = True
        self.fields['sexo'].required = True
        self.fields['empresa'].required = True
        self.fields['area'].required = True
        self.fields['cargo'].required = True
        self.fields['fecha_ingreso'].required = True
        self.fields['fecha_cese'].required = False

        if 'sexo' in self.fields:
            self.fields['sexo'].choices = [('', 'Seleccionar Sexo')] + list(self.fields['sexo'].choices)[1:]
        
        if 'empresa' in self.fields:
            # Esto quita el "--------" y pone un texto guía
            self.fields['empresa'].empty_label = "Seleccionar Empresa"

        if 'area' in self.fields:
            # Esto quita el "--------" y permite elegir las áreas creadas en la BD
            self.fields['area'].empty_label = "Seleccionar Área"
        
        if 'cargo' in self.fields:
            # El modelo guarda cargo como texto; por eso reemplazamos el campo por un ChoiceField.
            cargo_choices = [('', 'Seleccionar Cargo')] + [
                (cargo.nombre, cargo.nombre) for cargo in Cargo.objects.order_by('nombre')
            ]
            current_value = self.initial.get('cargo') or getattr(self.instance, 'cargo', '')
            self.fields['cargo'] = forms.ChoiceField(
                choices=cargo_choices,
                required=True,
                widget=forms.Select(attrs={'class': 'form-select form-control'})
            )
            self.fields['cargo'].initial = current_value or ''
# ======================================================
# FORMULARIOS PARA GESTIÓN DE CALENDARIO Y ASISTENCIA

from django import forms
import json

class UbicacionForm(forms.ModelForm):
    # --- ¡¡¡MODIFICACIÓN CLAVE AQUÍ!!! ---
    # Al decirle a Django que "localice" estos campos, 
    # automáticamente entenderá tanto '.' como ',' como separadores decimales.
    latitud = forms.FloatField(localize=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}))
    longitud = forms.FloatField(localize=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}))
    # ------------------------------------

    class Meta:
        model = Ubicacion
        fields = ['nombre', 'hora_entrada', 'latitud', 'longitud', 'radio']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'hora_entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            # Ya definimos los widgets para latitud y longitud arriba, así que no es necesario aquí.
            'radio': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
class JustificacionForm(forms.Form):
    # Usaremos un ChoiceField para seleccionar al trabajador
    trabajador_dni = forms.ChoiceField(label="Trabajador")
    fechaInicio = forms.DateField(label="Fecha de Inicio", widget=forms.DateInput(attrs={'type': 'date'}))
    fechaFin = forms.DateField(label="Fecha de Fin", widget=forms.DateInput(attrs={'type': 'date'}))
    tipo = forms.ChoiceField(
        label="Tipo de Justificación",
        choices=[
            ('Licencia Médica', 'Licencia Médica'),
            ('Vacaciones', 'Vacaciones'),
            ('Permiso Personal', 'Permiso Personal'),
            ('Trabajo Remoto', 'Trabajo Remoto'),
            ('Otro', 'Otro'),
        ]
    )
    descripcion = forms.CharField(label="Descripción (Opcional)", required=False, widget=forms.Textarea(attrs={'rows': 3}))

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        # Incluimos todos los nuevos campos
        fields = ['nombre', 'ruc', 'direccion', 'telefono', 'email_contacto']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre de la empresa'}),
            'ruc': forms.TextInput(attrs={'placeholder': 'RUC de 11 dígitos'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Dirección fiscal o principal'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Teléfono de contacto'}),
            'email_contacto': forms.EmailInput(attrs={'placeholder': 'correo@empresa.com'}),
        }
    def clean_ruc(self):
        ruc = self.cleaned_data.get('ruc')
        if ruc: # Solo valida si se ingresó algo
            if not ruc.isdigit():
                raise forms.ValidationError("El RUC solo debe contener números.")
            if len(ruc) != 11:
                raise forms.ValidationError("El RUC debe tener exactamente 11 dígitos.")
        return ruc
    
class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ['codigo', 'nombre', 'descripcion']
        widgets = {
            'codigo': forms.TextInput(attrs={'placeholder': 'Ej: TEC-01'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Técnico de Campo'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción de las funciones del cargo (opcional)'}),
        }

class PermisosAsistenciaForm(forms.Form):
    ubicacionesPermitidas = forms.MultipleChoiceField(
        label="Ubicaciones Permitidas para Marcar",
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        # Incluye aquí los campos que quieres que se puedan editar
        fields = ['nombre', 'trabajadores_permitidos'] 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'trabajadores_permitidos': forms.SelectMultiple(attrs={'class': 'form-control select2'}), # select2 es opcional para estilos
        }
        labels = {
            'nombre': 'Nombre del Dispositivo',
            'trabajadores_permitidos': 'Trabajadores Autorizados'
        }
