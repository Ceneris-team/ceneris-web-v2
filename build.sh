#!/usr/bin/env bash
# exit on error
set -o errexit
echo "--- [BUILD.SH] INICIADO ---"

echo ">>>> Recopilando archivos estáticos..."
python manage.py collectstatic --no-input
chmod -R a+r staticfiles/

echo ">>>> Aplicando migraciones de la base de datos..."
python manage.py migrate

#python manage.py import_maestros datos_maestros.xlsx --clean
#python manage.py import_maestros datos_maestros.xlsx
#python manage.py importar_certificados_pdf certificados_pdf/
#python manage.py importar_certificados_fijos_pdf certificados_fijos_pdf/

echo ">>>> Build finalizado exitosamente."