from django import forms
from .models import Insumo, RegistroReparacion, ItemInsumo

class CrearInsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'descripcion', 'unidad_medida', 'costo_unitario_actual']

class InsumoUpdateForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = [ 'costo_unitario_actual']

class RegistroReparacionForm(forms.ModelForm):

    class Meta: 
        model = RegistroReparacion
        fields = ['fecha_reporte', 'descripcion', 'costo']
        widgets = {
            'fecha_reporte': forms.DateInput(attrs={'type': 'date'}),
        
        }

class ItemInsumoForm(forms.ModelForm):
    """
    Formulario para crear y editar un ItemInsumo individual.
    """
    class Meta:
        model = ItemInsumo
        # Excluimos los campos que se asignan automáticamente
        exclude = ['insumo_padre', 'estado']
        
        # Añadimos widgets para mejorar la apariencia de los campos
        widgets = {
            'codigo_interno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: EQ-001'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'accesorios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'serie_accesorio': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_calibracion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_prox_calibracion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }