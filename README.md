# CENERIS Web v2 — Monorepo

Backend Django + frontend Flutter para gestión de calidad, RRHH, administración, inventario, proyectos, cotizaciones y accesos.

## Estructura del monorepo

```
v2/
├── admin_panel/          # Config Django (settings, urls, wsgi, asgi, db_router)
├── apps/                 # Todas las apps Django agrupadas
│   ├── accesos/
│   ├── administracion/
│   ├── api/
│   ├── calidad/
│   ├── cenerisapp/       # app principal
│   ├── cotizaciones/
│   ├── inventario/
│   ├── metricas_ceneris/
│   ├── personal/
│   ├── proyecto_monitoreo_smcv/
│   ├── proyectos/
│   └── recursoshumanos/
│
├── flutter_app/          # Frontend Flutter (ver flutter_app/README.md)
│
├── scripts/              # Utilitarios one-off (importar_excel, migrar_a_firebase, etc.)
│   └── debug_emails/     # HTMLs de depuración de correos
├── tests_manuales/       # Tests exploratorios (test_emo_*)
│
├── data/                 # Fixtures y datos históricos (versionados)
│   ├── datos_maestros.xlsx
│   ├── importacion_inventario.xlsx
│   ├── reporte_asistencias.xlsx
│   ├── importacion_emos.csv
│   └── pdfs_historicos/  # certificados, confirmaciones, controles
│
├── deploy/
│   └── policies/         # IAM policies (S3, etc.)
│
├── secrets/              # 🔒 Ignorada por git. Credenciales locales.
├── media/                # 🔒 Runtime uploads (ignorada por git)
├── static/               # CSS, JS, imágenes servidas por whitenoise
│
├── Dockerfile
├── build.sh              # Script de build (Render)
├── render.yaml
├── maintenance.html
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

**Nota sobre `apps/`:** en `admin_panel/settings.py` se inyecta `apps/` en `sys.path`, por lo que en `INSTALLED_APPS` las apps se listan con el nombre corto (`'calidad'`, `'cenerisapp'`, etc.) y todos los imports internos siguen funcionando sin prefijo `apps.`.

---

## Backend Django

### Requisitos

- **Python 3.13+** (recomendado 3.13.7 o 3.14.1).
- **GTK3 Runtime** (OBLIGATORIO para generar PDFs con WeasyPrint):
  - Descarga: <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases>
  - Instala `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe` y marca **"Add to PATH"**.
  - MSYS2 opcional: `winget install MSYS2.MSYS2`.

### Instalación

```powershell
# 1. Clonar
git clone https://github.com/DEV-Ceneris/ceneris-web.git v2
cd v2

# 2. Virtualenv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar .env
Copy-Item .env.example .env
# Editar valores. Para desarrollo local basta con:
#   SECRET_KEY=django-insecure-...
#   DJANGO_DEBUG=True
#   DATABASE_URL=sqlite:///db.sqlite3
#   USE_FIRESTORE=False

# 5. Credenciales de Firebase (sólo si USE_FIRESTORE=True)
# Colocar el JSON de la service account en:
#   secrets/firebase-service-account.json
# (la carpeta secrets/ está ignorada por git)

# 6. Migraciones + superuser
python manage.py migrate
python manage.py createsuperuser

# 7. Correr
python manage.py runserver
```

Abrir:
- App: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>

### Comandos frecuentes

```powershell
# Migraciones
python manage.py migrate
python manage.py makemigrations
python manage.py migrate --plan               # ver qué se aplicaría sin ejecutar

# Estáticos
python manage.py collectstatic --no-input

# Importar datos maestros
python manage.py import_maestros data/datos_maestros.xlsx

# Scripts one-off (ejecutar desde la raíz del proyecto)
python scripts/importar_excel.py
python scripts/migrar_a_firebase.py           # requiere POSTGRES_MIGRATION_URL en .env
python scripts/recalcular_tardanzas.py
```

---

## Frontend Flutter

Ver [`flutter_app/README.md`](flutter_app/README.md). Al momento de esta v2 la carpeta contiene sólo scaffolding (`.gitignore` + README con la estructura target feature-first). El bootstrap real se hace con:

```bash
cd flutter_app
flutter create . --org com.ceneris --project-name ceneris_app --platforms=android,ios
flutter pub get
flutter run
```

---

## Variables de entorno

Ver `.env.example` para la lista completa. Mínimo para desarrollo:

| Variable | Ejemplo | Notas |
|---|---|---|
| `SECRET_KEY` | `django-insecure-...` | Cambiar en producción |
| `DJANGO_DEBUG` | `True` | `False` en producción |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | O `postgresql://...` |
| `USE_FIRESTORE` | `False` | `True` requiere credenciales Firebase |

Opcionales / producción: `FIREBASE_SERVICE_ACCOUNT_JSON_BASE64`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `SENDGRID_API_KEY`, `EMAIL_HOST_PASSWORD`, `POSTGRES_MIGRATION_URL`.

---

## Producción (Render)

Build command lo maneja [`build.sh`](build.sh) (`collectstatic` + `migrate`). Config en [`render.yaml`](render.yaml). Variables mínimas:

```env
SECRET_KEY=<clave-larga-generada>
DJANGO_DEBUG=False
DATABASE_URL=postgresql://user:pass@host:5432/db
USE_FIRESTORE=True
FIREBASE_SERVICE_ACCOUNT_JSON_BASE64=<base64 del JSON de la service account>
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_STORAGE_BUCKET_NAME=asistencia-ceneris-media
AWS_S3_REGION_NAME=us-east-1
EMAIL_HOST_PASSWORD=<app-password de gmail>
```

Arrancar con Gunicorn:

```bash
gunicorn admin_panel.wsgi:application
```

---

## Seguridad — reglas del repo

- **Nunca** commitear archivos en `secrets/` (la carpeta está ignorada, pero verificar antes de push).
- **Nunca** hardcodear credenciales en `settings.py` ni en scripts. Usar `os.environ.get(...)` con default `None` y fallar rápido si falta.
- Rotar cualquier credencial que haya estado en el árbol de trabajo aunque no haya sido commiteada.
- El `.gitignore` bloquea patrones específicos de service accounts (`firebase-service-account*.json`, `*serviceAccount*.json`, etc.) — no reintroducir un `*.json` global.

---

## Solución de problemas

| Síntoma | Causa probable | Fix |
|---|---|---|
| `ImportError: Couldn't import Django` | venv no activado | `. .venv/Scripts/Activate.ps1` |
| `manage.py migrate` propone TODAS las migraciones | `db.sqlite3` no existe (ignorado por git) | Normal en checkout nuevo; corre `migrate` una vez |
| Error al generar PDFs | GTK3 Runtime no en PATH | Reinstalar y marcar "Add to PATH" |
| `ADVERTENCIA: Archivo de credenciales de Firebase no encontrado` | Falta `secrets/firebase-service-account.json` | Copiar el JSON ahí, o setear `FIREBASE_SERVICE_ACCOUNT_JSON_BASE64` |
| `ModuleNotFoundError: No module named 'calidad'` (u otra app) | `apps/` no está en `sys.path` — settings.py fue editada mal | Revisar el bloque `APPS_DIR = BASE_DIR / 'apps'` cerca del inicio de `admin_panel/settings.py` |
