#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Force default storage to use the configured storage backend early in
    # development so code that imported default_storage at import time will
    # use S3 when env vars are present. This is a safe, non-destructive
    # dev-time helper and only runs if Django settings are available.
    try:
        # Import settings now that DJANGO_SETTINGS_MODULE is set
        from django.conf import settings
        if getattr(settings, 'DEBUG', False):
            from django.utils.module_loading import import_string
            from django.core.files.storage import default_storage
            StorageClass = import_string(settings.DEFAULT_FILE_STORAGE)
            # Create an instance and replace the wrapped storage
            default_storage._wrapped = StorageClass()
            print(f"[manage.py] Forced default_storage to {default_storage._wrapped.__class__}")
    except Exception as _e:
        # Do not prevent manage commands from running; only log for dev.
        try:
            print(f"[manage.py] Warning: could not force default_storage: {_e}")
        except Exception:
            pass
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
