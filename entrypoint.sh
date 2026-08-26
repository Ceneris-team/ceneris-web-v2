#!/usr/bin/env bash
# Arranque del contenedor web.
#
# En Render esto lo hacia build.sh via buildCommand. En Lightsail no existe esa
# etapa, asi que migrate y collectstatic corren aca, en cada arranque.
set -o errexit

echo "--- [ENTRYPOINT] INICIADO ---"

echo ">>>> Aplicando migraciones de la base de datos..."
python manage.py migrate --no-input

# Obligatorio: settings usa CompressedManifestStaticFilesStorage, que lanza
# excepcion en cada {% static %} si no existe el manifiesto.
echo ">>>> Recopilando archivos estaticos..."
python manage.py collectstatic --no-input

echo ">>>> Arrancando gunicorn en 0.0.0.0:${PORT:-8000}..."
exec gunicorn admin_panel.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --timeout 120 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - \
    --error-logfile -
