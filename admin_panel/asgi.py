"""
ASGI config for admin_panel project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')

application = get_asgi_application()

# Mirror the WSGI startup behavior: if AWS env vars are present, instantiate
# and assign the configured storage backend to `default_storage` so ASGI workers
# use S3-backed storage rather than a prematurely-initialized FileSystemStorage.
try:
	import os as _os
	if _os.environ.get('AWS_ACCESS_KEY_ID') and _os.environ.get('AWS_SECRET_ACCESS_KEY') and _os.environ.get('AWS_STORAGE_BUCKET_NAME'):
		from django.conf import settings as _settings
		from django.utils.module_loading import import_string as _import_string
		from django.core.files.storage import default_storage as _default_storage
		StorageClass = _import_string(_settings.DEFAULT_FILE_STORAGE)
		_default_storage._wrapped = StorageClass()
		print(f"[asgi.py] Forced default_storage to {_default_storage._wrapped.__class__}")
except Exception as _e:
	try:
		print(f"[asgi.py] Warning: could not force default_storage at startup: {_e}")
	except Exception:
		pass
