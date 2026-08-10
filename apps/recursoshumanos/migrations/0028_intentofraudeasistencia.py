from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recursoshumanos', '0027_trabajador_areas_supervisadas'),
    ]

    operations = [
        migrations.CreateModel(
            name='IntentoFraudeAsistencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('user_name', models.CharField(blank=True, default='', max_length=255)),
                ('user_dni', models.CharField(blank=True, db_index=True, default='', max_length=20)),
                ('reason', models.CharField(blank=True, default='', max_length=255)),
                ('blocked_reason', models.CharField(blank=True, default='', max_length=255)),
                ('security_reason', models.CharField(blank=True, default='', max_length=255)),
                ('device_id', models.CharField(blank=True, default='', max_length=255)),
                ('location_name', models.CharField(blank=True, default='', max_length=255)),
                ('reported_latitude', models.FloatField(blank=True, null=True)),
                ('reported_longitude', models.FloatField(blank=True, null=True)),
                ('source', models.CharField(blank=True, default='', max_length=100)),
                ('raw_payload', models.JSONField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='intentofraudeasistencia',
            index=models.Index(fields=['timestamp'], name='rhh_fraude_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='intentofraudeasistencia',
            index=models.Index(fields=['user_dni'], name='rhh_fraude_dni_idx'),
        ),
    ]
