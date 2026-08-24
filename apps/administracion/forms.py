# administracion/forms.py

from django import forms
from decimal import Decimal, InvalidOperation
import datetime
from .models import Requerimiento, RegistroConsumo, Agente, Feriado

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


class FeriadoForm(forms.ModelForm):
    """Formulario de registro/edición de feriados (HU-01 CAV-10)."""

    class Meta:
        model = Feriado
        fields = ['fecha', 'nombre', 'tipo', 'ambito', 'sede', 'empresa']
        widgets = {
            'fecha': forms.DateInput(
                attrs={'type': 'date', 'class': 'modal-input'},
                format='%Y-%m-%d',
            ),
            'nombre': forms.TextInput(
                attrs={'class': 'modal-input', 'maxlength': 150,
                       'placeholder': 'Ej: Año Nuevo'}
            ),
            'tipo': forms.Select(attrs={'class': 'modal-input'}),
            'ambito': forms.Select(attrs={'class': 'modal-input'}),
            'sede': forms.Select(attrs={'class': 'modal-input'}),
            'empresa': forms.Select(attrs={'class': 'modal-input'}),
        }

    def clean_fecha(self):
        """Valida que no exista otro feriado en la misma fecha (CAV-54).

        El texto del error es el exigido literalmente por la HU. Al levantar
        aquí, 'fecha' sale de cleaned_data y se evita que la validación unique
        automática del modelo agregue un segundo mensaje distinto.
        """
        fecha = self.cleaned_data['fecha']
        qs = Feriado.objects.filter(fecha=fecha)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Ya existe un feriado registrado para la fecha seleccionada"
            )
        return fecha

    def clean(self):
        """Coherencia entre ámbito y scope (CAV-13).

        Un feriado regional/local exige Sede; uno de empresa exige Empresa; el
        nacional no debe llevar ninguno (aplica a todos).
        """
        cleaned = super().clean()
        ambito = cleaned.get('ambito')
        sede = cleaned.get('sede')
        empresa = cleaned.get('empresa')

        if ambito in (Feriado.Ambito.REGIONAL, Feriado.Ambito.LOCAL):
            if not sede:
                self.add_error('sede', 'Un feriado regional/local requiere una sede.')
            if empresa:
                self.add_error('empresa', 'Un feriado regional/local no lleva empresa.')
        elif ambito == Feriado.Ambito.EMPRESA:
            if not empresa:
                self.add_error('empresa', 'Un feriado de empresa requiere una empresa.')
            if sede:
                self.add_error('sede', 'Un feriado de empresa no lleva sede.')
        elif ambito == Feriado.Ambito.NACIONAL:
            if sede:
                self.add_error('sede', 'Un feriado nacional aplica a todos: deje la sede vacía.')
            if empresa:
                self.add_error('empresa', 'Un feriado nacional aplica a todos: deje la empresa vacía.')
        return cleaned

