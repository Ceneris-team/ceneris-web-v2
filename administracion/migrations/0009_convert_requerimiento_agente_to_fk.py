# Generated data migration to convert Requerimiento.agente (string) into FK to Agente
from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    Requerimiento = apps.get_model('administracion', 'Requerimiento')
    Agente = apps.get_model('administracion', 'Agente')
    db_alias = schema_editor.connection.alias

    # 1) Add temporary Agente FK field (agente_fk) - created by migration operations below
    # 2) Populate agente_fk by finding/creating Agente rows matching existing string names
    for req in Requerimiento.objects.using(db_alias).all():
        # old value stored in the model instance might still be accessible as attribute
        try:
            agent_name = getattr(req, 'agente')
        except Exception:
            agent_name = None

        if not agent_name:
            continue

        agent_obj, created = Agente.objects.using(db_alias).get_or_create(nombre_agente=agent_name, defaults={'activo': True, 'precio_unitario': 0})
        # set temporary fk attribute; the migration operation will add the actual field on the model in the project,
        # but here we set the value directly on the DB via update to avoid model state mismatch.
        Requerimiento.objects.using(db_alias).filter(pk=req.pk).update(agente_fk_id=agent_obj.pk)


def backwards(apps, schema_editor):
    Requerimiento = apps.get_model('administracion', 'Requerimiento')
    Agente = apps.get_model('administracion', 'Agente')
    db_alias = schema_editor.connection.alias

    # Recreate the string agent values from the agente_fk relation
    for req in Requerimiento.objects.using(db_alias).all():
        fk_id = getattr(req, 'agente_fk_id', None)
        if fk_id:
            try:
                agente = Agente.objects.using(db_alias).get(pk=fk_id)
                Requerimiento.objects.using(db_alias).filter(pk=req.pk).update(agente=agente.nombre_agente)
            except Agente.DoesNotExist:
                # leave existing value as-is
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('administracion', '0008_add_precio_unitario_agente'),
    ]

    operations = [
        # Add a temporary FK field 'agente_fk' to hold references while we migrate data
        migrations.AddField(
            model_name='requerimiento',
            name='agente_fk',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, to='administracion.agente'),
        ),
        migrations.RunPython(forwards, backwards),
        # Remove the old string field 'agente' (if it exists in DB schema)
        migrations.RemoveField(
            model_name='requerimiento',
            name='agente',
        ),
        # Rename the temporary FK to the canonical name 'agente'
        migrations.RenameField(
            model_name='requerimiento',
            old_name='agente_fk',
            new_name='agente',
        ),
    ]
