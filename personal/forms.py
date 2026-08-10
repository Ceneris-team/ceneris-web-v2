from django import forms
from .models import Personal, AreaTrabajo

class PersonalForm(forms.ModelForm):
    class Meta: 
        model= Personal
        fields = ['area_trabajo', 'nombre', 'apellido', 'foto','dni', 'cargo', 'correo', 'telefono']

class AreaTrabajoForm(forms.ModelForm):
    class Metas: 
        model = AreaTrabajo
        fields = ['nombre']