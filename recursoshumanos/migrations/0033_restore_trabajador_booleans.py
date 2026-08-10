# Generated manually to reconcile DB schema with current Trabajador model.

from django.db import migrations, models


def _migrar_nivel_a_booleans(apps, schema_editor):
    Trabajador = apps.get_model('recursoshumanos', 'Trabajador')

    for trabajador in Trabajador.objects.all().only('id', 'nivel_jerarquico'):
        nivel = (getattr(trabajador, 'nivel_jerarquico', '') or '').upper()

        if nivel == 'GERENTE':
            trabajador.es_jefe = False
            trabajador.es_gerente = True
        elif nivel == 'RESPONSABLE':
            trabajador.es_jefe = True
            trabajador.es_gerente = True
        elif nivel == 'SUPERVISOR':
            trabajador.es_jefe = True
            trabajador.es_gerente = False
        else:
            trabajador.es_jefe = False
            trabajador.es_gerente = False

        trabajador.save(update_fields=['es_jefe', 'es_gerente'])


def _reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('recursoshumanos', '0032_remove_trabajador_es_gerente_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajador',
            name='es_jefe',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='trabajador',
            name='es_gerente',
            field=models.BooleanField(default=False, verbose_name='Es Gerente General'),
        ),
        migrations.RunPython(_migrar_nivel_a_booleans, _reverse_noop),
        migrations.RemoveField(
            model_name='trabajador',
            name='nivel_jerarquico',
        ),
        migrations.AlterField(
            model_name='trabajador',
            name='areas_supervisadas',
            field=models.ManyToManyField(blank=True, related_name='jefes_supervisores', to='recursoshumanos.area', verbose_name='Áreas Supervisadas (Jefatura)'),
        ),
    ]
