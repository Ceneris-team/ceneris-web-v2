from django.db import models
from django.utils import timezone
from recursoshumanos.models import Trabajador

class EvaluacionMensual(models.Model):
    TIPOS_EVALUACION = [
        ('MENSUAL', 'Evaluación Mensual'),
        ('SEMESTRAL', 'Evaluación Semestral'),
        ('NUEVO', 'Evaluación Nuevo Ingreso'),
    ]

    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='evaluaciones')
    evaluador = models.ForeignKey(
        
        Trabajador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluaciones_realizadas'
    )
    cargo_evaluador = models.CharField(max_length=150, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_EVALUACION, default='MENSUAL') # <-- NUEVO CAMPO
    fecha_evaluacion = models.DateField(default=timezone.now)
    promedio_final = models.FloatField(default=0.0)
    comentario_general = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_evaluacion', '-id']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.trabajador} - {self.fecha_evaluacion.strftime('%B %Y')}"
class Puntaje(models.Model):
    CATEGORIAS = [
        ('OPERACIONAL', '2.1 Operacional'),
        ('ADMINISTRATIVO', '2.2 Administrativo'),
        ('HABILIDADES', '2.3 Habilidades Blandas'),
    ]
    
    evaluacion = models.ForeignKey(EvaluacionMensual, on_delete=models.CASCADE, related_name='puntajes')
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    indicador_nombre = models.CharField(max_length=100)
    nota = models.IntegerField() # Del 1 al 10

    def __str__(self):
        return f"{self.indicador_nombre}: {self.nota}"