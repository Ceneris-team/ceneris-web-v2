from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recursoshumanos', '0026_asistencia_origen'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajador',
            name='areas_supervisadas',
            field=models.ManyToManyField(
                blank=True,
                related_name='jefes_supervisores',
                to='recursoshumanos.area',
                verbose_name='Áreas Supervisadas (Jefatura)',
            ),
        ),
    ]
