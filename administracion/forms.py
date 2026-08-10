# administracion/forms.py

from django import forms
from decimal import Decimal, InvalidOperation
import datetime
from .models import Requerimiento, RegistroConsumo, Agente

class RequerimientoForm(forms.ModelForm):
    # --- ¡CAMBIO CLAVE AQUÍ! ---
    # Usamos un ModelChoiceField. Este campo generará automáticamente
    # un <select> con todos los agentes activos de la base de datos.
    agente = forms.ModelChoiceField(
        queryset=Agente.objects.filter(activo=True),
        empty_label="Seleccione un agente",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # El tipo de monitoreo lo dejamos como estaba, pero con un empty_label
    tipo_monitoreo = forms.ChoiceField(
        choices=[('', 'Seleccione un tipo')] + Requerimiento.TIPO_MONITOREO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Requerimiento
        # Los campos ahora coinciden con el modelo actualizado
        fields = ['tipo_monitoreo', 'agente', 'cantidad_total']
        widgets = {
            'cantidad_total': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class RegistroConsumoForm(forms.ModelForm):
    # Hacemos que el año por defecto sea el actual
    año = forms.IntegerField(
        initial=datetime.date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = RegistroConsumo
        fields = ['mes', 'año', 'cantidad_consumida']
        widgets = {
            'mes': forms.Select(attrs={'class': 'form-select'}),
            # Permitimos decimales: step '0.01' y placeholder con ejemplo decimal
            'cantidad_consumida': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150.50', 'step': '0.01', 'inputmode': 'decimal'}),
        }

    def clean_cantidad_consumida(self):
        """Normaliza entradas con coma decimal y valida como Decimal."""
        value = self.cleaned_data.get('cantidad_consumida')
        # Si ya es Decimal/float/int, devolver tal cual
        if value is None:
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            # Intentar leer el valor crudo del POST y reemplazar coma por punto
            raw = self.data.get(self.add_prefix('cantidad_consumida'))
            if raw:
                raw = raw.replace(',', '.')
                try:
                    return Decimal(raw)
                except InvalidOperation:
                    raise forms.ValidationError('Ingrese un número válido (p. ej. 150.50).')
            raise forms.ValidationError('Ingrese un número válido.')

