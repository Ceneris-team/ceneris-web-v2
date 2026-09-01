from django import forms
from .models import EvaluacionMensual

# Configuración centralizada de indicadores y descripciones
ESTRUCTURA_EVALUACION = {
    'OPERACIONAL': [
        ('tiempo_entrega', 'Tiempo de entrega', 'Culmina las actividades en el tiempo establecido.'),
        ('calidad_trabajo', 'Cumplimiento de sus actividades', 'Cierre de tareas y actividades encomendadas por el jede de inmediata.'),
        ('conocimiento_campo', 'Conocimiento sobre sus funciones', 'Conocer funciones sobre su puesto de trabajo.'),
        ('cuidado_elementos', 'Cuidado con sus elementos de trabajo', 'Mantenimiento y resguardo de equipos.'),
    ],
    'ADMINISTRATIVO': [
        ('recibe_ordenes', 'Recibe órdenes y responde claro', 'Capacidad de escucha y feedback efectivo.'),
        ('relacion_entorno', 'Relación con entorno al grupo', 'Clima laboral y compañerismo.'),
        ('comunicacion_cliente', 'Comunicación usuario/cliente', 'Trato cordial y efectivo con clientes internos/externos.'),
        ('cuestionamiento', 'Cuestionamiento de orden', 'Capacidad crítica constructiva.'),
        ('compromiso_sst', 'Compromiso y participación en SST', 'Seguridad y Salud en el Trabajo.'),
        ('compromiso_ambiente', 'Compromiso y participación en medio ambiente', 'Cuidado y respeto por el medio ambiente.'),
    ],
    'HABILIDADES': [
        ('empatia', 'Empatía', 'Capacidad de entender las necesidades ajenas.'),
        ('proactividad', 'Proactividad', 'Iniciativa para resolver problemas sin esperar ordenes.'),
        ('presentacion', 'Presentación', 'Imagen personal acorde al puesto.'),
        ('liderazgo', 'Liderazgo', 'Capacidad de influir positivamente en otros.'),
        ('respeto', 'Respeto', 'Trato digno hacia todos los niveles jerárquicos.'),
        ('Organizacion', 'Organización', 'Capacidad de planificar y ordenar tareas.'),
    ]
}

class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = EvaluacionMensual
        fields = ['comentario_general']
        widgets = {
            'comentario_general': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        puntajes_iniciales = kwargs.pop('puntajes_iniciales', {}) or {}
        super().__init__(*args, **kwargs)
        # Generamos dinámicamente los campos del 1 al 10
        OPCIONES_NOTA = [(i, str(i)) for i in range(1, 11)]

        for categoria, indicadores in ESTRUCTURA_EVALUACION.items():
            for clave, nombre, desc in indicadores:
                field_name = f"ind_{clave}"
                self.fields[field_name] = forms.ChoiceField(
                    choices=OPCIONES_NOTA,
                    label=nombre,
                    help_text=desc, # Usaremos esto para el tooltip
                    widget=forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white shadow-sm focus:ring-indigo-500'})
                )
                if field_name in puntajes_iniciales:
                    self.fields[field_name].initial = puntajes_iniciales[field_name]