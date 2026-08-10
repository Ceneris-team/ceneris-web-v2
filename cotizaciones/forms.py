# cotizaciones/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Cotizaciones, Empresa, Contacto, ProcesoCotizacion , DetalleCotizacion

class AgendarCitaForm(forms.Form):
    # Campos para la Empresa
    nombre_empresa = forms.CharField(label="Nombre de la Empresa", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    ruc = forms.CharField(label="RUC de la Empresa", max_length=13, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_ruc'}))
    ubicacion = forms.CharField(label="Ubicación", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # Campos para el Contacto
    nombre_contacto = forms.CharField(label="Nombre del Contacto", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    correo = forms.EmailField(label="Correo del Contacto", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(label="Teléfono del Contacto", max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Campo para el Proceso de Cotización
    fecha_citacion = forms.DateTimeField(
        label="Fecha de la Cita",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
class RegistrarEncuentroForm(forms.ModelForm):
    class Meta:
        model = ProcesoCotizacion
        # Campo para la segunda etapa
        fields = ['fecha_encuentro']
        widgets = {
            'fecha_encuentro': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
class CrearCotizacionForm(forms.ModelForm):
    class Meta:
        model = ProcesoCotizacion
        # Campo para la segunda etapa
        fields = ['fecha_encuentro']
        widgets = {
            'fecha_encuentro': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class CotizacionForm(forms.ModelForm):
    # Campos de Empresa
    nombre_empresa = forms.CharField(label="Nombre de la Empresa", max_length=255)
    ruc = forms.CharField(label="RUC", max_length=13)
    ubicacion = forms.CharField(label="Ubicación", max_length=255, required=False)

    # Campos de Contacto
    nombre_contacto = forms.CharField(label="Nombre del Contacto", max_length=255)
    correo = forms.EmailField(label="Correo Electrónico")
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)

    class Meta:
        model = Cotizaciones
        # Campos del modelo Cotizacion que queremos mostrar directamente
        fields = ['descripcion_pedido', 'tipo_servicio_producto']
        widgets = {
            'descripcion_pedido': forms.Textarea(attrs={'rows': 4}),
        }

class CotizacionPrincipalForm(forms.ModelForm):
    class Meta:
        model = Cotizaciones
        fields = ['descripcion_pedido', 'tipo_servicio_producto']
    

class DetalleCotizacionForm(forms.ModelForm):
    class Meta:
        model = DetalleCotizacion
        fields = ['descripcion', 'cantidad', 'precio_unitario']

# Creamos el Formset que une la cotización con sus detalles
# extra=1 para que siempre muestre al menos una fila vacía
DetalleCotizacionFormSet = inlineformset_factory(
    Cotizaciones, 
    DetalleCotizacion, 
    form=DetalleCotizacionForm,
    extra=1, 
    can_delete=True
)

class EmpresaForm(forms.ModelForm):
    """Formulario para registrar una nueva empresa en la base de datos central."""
    class Meta:
        model = Empresa
        fields = ['nombre', 'ruc', 'ubicacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Empresa S.A.C.'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '20123456789'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Av. Principal 123, Lima'}),
        }