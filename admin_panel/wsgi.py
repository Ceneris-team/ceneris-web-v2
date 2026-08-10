"""
WSGI config for admin_panel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')

application = get_wsgi_application()

# If AWS env vars are present (for example when running on Render), ensure the
# Django `default_storage` is instantiated with the configured storage backend
# at process startup. This avoids the situation where some modules import
# `default_storage` at import-time and get `FileSystemStorage` before settings
# and env vars are applied. We wrap this in a try/except so it never prevents
# the application from starting.
try:
	import os as _os
	if _os.environ.get('AWS_ACCESS_KEY_ID') and _os.environ.get('AWS_SECRET_ACCESS_KEY') and _os.environ.get('AWS_STORAGE_BUCKET_NAME'):
		from django.conf import settings as _settings
		from django.utils.module_loading import import_string as _import_string
		from django.core.files.storage import default_storage as _default_storage
		StorageClass = _import_string(_settings.DEFAULT_FILE_STORAGE)
		_default_storage._wrapped = StorageClass()
		print(f"[wsgi.py] Forced default_storage to {_default_storage._wrapped.__class__}")
except Exception as _e:
	try:
		print(f"[wsgi.py] Warning: could not force default_storage at startup: {_e}")
	except Exception:
		pass
