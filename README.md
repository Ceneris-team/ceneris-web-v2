# CENERIS Web - Sistema de Gestión Empresarial

Sistema Django para gestión de calidad, RRHH, administración, inventario, proyectos y cotizaciones.

## Inicializacion del proyecto

### Requisitos Previos

- **Python 3.13+** (recomendado 3.13.7 o 3.14.1)
- **GTK3 Runtime** (OBLIGATORIO para generar PDFs)
  - Descarga: [GTK3 Runtime Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
  - Instala: `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe`
  - **IMPORTANTE:** Durante la instalación, marca "Add to PATH"
  
winget install MSYS2.MSYS2

### Instalación

```powershell
# 1. Clonar el repositorio
git clone https://github.com/DEV-Ceneris/ceneris-web.git
cd ceneris-web

# 2. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
Copy-Item .env.example .env
# Edita .env con tus valores (por defecto ya funciona para desarrollo)

# 5. Preparar base de datos
python manage.py migrate
python manage.py createsuperuser

# 6. Iniciar servidor
python manage.py runserver
```

**Acceder a:**
- Aplicación: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

---

## ⚙️ Configuración (.env)

Copia `.env.example` a `.env` y configura las variables:

### Mínimo para Desarrollo Local

```env
SECRET_KEY=django-insecure-clave-desarrollo-local
DJANGO_DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
USE_FIRESTORE=False
```

### Variables Principales

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta Django | `django-insecure-...` |
| `DJANGO_DEBUG` | Modo debug (True/False) | `True` |
| `DATABASE_URL` | Conexión a base de datos | `sqlite:///db.sqlite3` o `postgresql://...` |
| `USE_FIRESTORE` | Usar Firebase (True/False) | `False` |
| `AWS_ACCESS_KEY_ID` | AWS S3 para archivos (opcional) | Sin esto, archivos locales en `media/` |
| `SENDGRID_API_KEY` | SendGrid para emails (opcional) | Sin esto, emails no se envían |

**Nota:** Para producción ver todas las variables en `.env.example`

---

## 📋 Comandos Útiles

```powershell
# Base de datos
python manage.py migrate                   # Aplicar migraciones
python manage.py makemigrations            # Crear nuevas migraciones
python manage.py createsuperuser           # Crear admin

# Servidor
python manage.py runserver                 # Iniciar desarrollo

# Archivos estáticos
python manage.py collectstatic --no-input # Recolectar estáticos

# Datos
python manage.py import_maestros datos_maestros.xlsx  # Importar datos
```

---

## Estructura del Proyecto

```
ceneris-web/
├── admin_panel/          # Configuración Django
├── administracion/       # Módulo administración
├── calidad/             # Módulo calidad y certificados
├── cenerisapp/          # Aplicación principal
├── cotizaciones/        # Módulo cotizaciones
├── inventario/          # Módulo inventario
├── personal/            # Módulo personal
├── proyectos/           # Módulo proyectos
├── recursoshumanos/     # Módulo RRHH
├── static/              # CSS, JS, imágenes
├── media/               # Archivos subidos
├── scripts/             # Scripts PowerShell de utilidad
├── manage.py
├── requirements.txt
└── .env                 # Tu configuración (NO subir a Git)
```

---

## Producción

### Variables de Entorno Requeridas

```env
SECRET_KEY=<generar-clave-larga-segura>
DJANGO_DEBUG=False
DATABASE_URL=postgresql://user:pass@host:5432/db
USE_FIRESTORE=True
FIREBASE_SERVICE_ACCOUNT_JSON_BASE64=<base64-encoded-json>
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_STORAGE_BUCKET_NAME=asistencia-ceneris-media
AWS_S3_REGION_NAME=us-east-1
```

### Comandos de Deploy

```powershell
# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Aplicar migraciones
python manage.py migrate

# Iniciar con Gunicorn
gunicorn admin_panel.wsgi:application
```

---

## Solución de Problemas

### Error al generar PDFs
- **Causa:** GTK3 Runtime no instalado o no en PATH
- **Solución:** Reinstalar GTK3 Runtime y marcar "Add to PATH"

### Variables de entorno no se cargan
- **Causa:** Archivo `.env` no existe o mal configurado
- **Solución:** Copiar `.env.example` a `.env` y verificar valores

### Error de base de datos
- **Causa:** Migraciones no aplicadas
- **Solución:** `python manage.py migrate`

---

