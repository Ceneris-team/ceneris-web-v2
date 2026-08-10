from django.db import models

class AreaTrabajo(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre


class Personal(models.Model):
    area_trabajo = models.ForeignKey(AreaTrabajo, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    dni = models.CharField(max_length=20, unique=True)
    cargo = models.CharField(max_length=50)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    foto = models.ImageField(upload_to='personal/fotos/', null=True, blank=True, default='personal/fotos/default-avatar.png')

    def initials(self):
        first_letter_nombre = self.nombre[0].upper() if self.nombre else ''
        first_letter_apellido = self.apellido[0].upper() if self.apellido else ''
        return f"{first_letter_nombre}{first_letter_apellido}"
        
    def __str__(self):
        return self.nombre
