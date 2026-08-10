from django import forms
from .models import Proyecto, TareaP, SubTarea
from django.core.exceptions import ValidationError
from personal.models import Personal
from datetime import date 

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'descripcion']
        

class ProyectoEditForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        # Incluimos todos los campos que se pueden editar
        fields = ['nombre', 'descripcion']
        # Usamos widgets para que los campos de fecha usen el selector de fecha del navegador
        

class TareaPForm(forms.ModelForm):
    class Meta:
        model = TareaP
        fields = ['titulo', 'descripcion', 'completada', 'proyecto']
        widgets = {
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

class SubTareaForm(forms.ModelForm):
    class Meta:
        model = SubTarea
        fields = ['titulo', 'descripcion', 'fecha_fin', 'completada', 'tarea']
        widgets = {
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    

class SubTareaEditForm(forms.ModelForm):
    class Meta:
        model = SubTarea
        fields = ['titulo', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
    def clean(self):
        """
        Método de validación que se ejecuta después de que cada campo individual
        ha sido limpiado. Ideal para validaciones que dependen de múltiples campos.
        """

        # 1. Obtenemos los datos ya limpios por Django
        cleaned_data = super().clean()
        
        # 2. Extraemos los valores de las fechas
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        # 3. La Lógica de Validación
        # Solo procedemos si ambos campos tienen datos válidos
        if fecha_inicio and fecha_fin:
            if fecha_fin < fecha_inicio:
                # 4. Si la condición no se cumple, lanzamos un ValidationError.
                # Django atrapará este error y lo mostrará en el formulario.
                raise ValidationError(
                    "Error de lógica: La fecha de fin no puede ser anterior a la fecha de inicio."
                )
        
        # 5. Siempre debemos devolver los datos limpios al final
        return cleaned_data