from django.db import migrations


# CAV-185: grupos que usa la matriz de control de acceso por plataforma.
# 'Recursos Humanos', 'Calidad' y 'Administrador' ya se usan en otras
# partes del sistema (p.ej. CustomLoginView); 'Supervisores' es nuevo.
GRUPOS_REQUERIDOS = [
    'Recursos Humanos',
    'Calidad',
    'Administrador',
    'Supervisores',
]


def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nombre in GRUPOS_REQUERIDOS:
        Group.objects.get_or_create(name=nombre)


def eliminar_grupos(apps, schema_editor):
    # No borramos nada al revertir: otros modulos ya dependen de estos
    # grupos (p.ej. el login) y podrian quedar usuarios asignados.
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, eliminar_grupos),
    ]
