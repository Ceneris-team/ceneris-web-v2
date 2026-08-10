# calidad/storages.py (NUEVO ARCHIVO)

from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class DebugS3Boto3Storage(S3Boto3Storage):
    """
    Un motor de almacenamiento S3 personalizado que imprime información de depuración
    en cada paso crítico para diagnosticar problemas de subida.
    Si no hay credenciales de S3, cae de vuelta a almacenamiento local.
    """
    def __init__(self, *args, **kwargs):
        # Este método se ejecuta cuando Django carga el motor de almacenamiento.
        print("\n--- [S3 DEBUG] INICIALIZANDO MOTOR DE ALMACENAMIENTO ---")
        
        # Verificar si hay credenciales de AWS
        has_aws_creds = settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY
        
        print(f"[S3 DEBUG] Valor de DEBUG: {settings.DEBUG}")
        print(f"[S3 DEBUG] AWS_ACCESS_KEY_ID: {'✓ Configurado' if settings.AWS_ACCESS_KEY_ID else '✗ NO CONFIGURADO (usará almacenamiento local)'}")
        print(f"[S3 DEBUG] AWS_SECRET_ACCESS_KEY: {'✓ Configurado' if settings.AWS_SECRET_ACCESS_KEY else '✗ NO CONFIGURADO (usará almacenamiento local)'}")
        
        if not has_aws_creds:
            print("[S3 DEBUG] ⚠️ Sin credenciales de AWS. Cambiando a almacenamiento local...")
            print("--- [S3 DEBUG] USANDO FileSystemStorage (local) ---\n")
            # No llamamos al __init__ de S3Boto3Storage si no hay credenciales
            # En su lugar, inicializamos un FileSystemStorage interno para delegar
            self._is_local = True
            
            # Inicializamos el FileSystemStorage que hará el trabajo real
            self._local_storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
            
            # Copiamos atributos esenciales o requeridos para compatibilidad básica
            self.location = settings.MEDIA_ROOT
            self.base_url = settings.MEDIA_URL
            
            # IMPORTANTE: Definir atributos que S3Boto3Storage o Django podrían buscar
            # para evitar AttributeErrors si se llama a métodos de la clase padre por accidente.
            self.file_overwrite = getattr(settings, 'AWS_S3_FILE_OVERWRITE', True) 
            self.object_parameters = {}
            self.custom_domain = None
        else:
            print(f"[S3 DEBUG] AWS_STORAGE_BUCKET_NAME: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '¡¡¡NO ENCONTRADO!!!')}")
            print(f"[S3 DEBUG] AWS_S3_REGION_NAME: {getattr(settings, 'AWS_S3_REGION_NAME', '¡¡¡NO ENCONTRADO!!!')}")
            print(f"[S3 DEBUG] AWS_DEFAULT_ACL: {getattr(settings, 'AWS_DEFAULT_ACL', 'No definido (usando el por defecto)')}")
            
            super().__init__(*args, **kwargs)
            self._is_local = False
            print("--- [S3 DEBUG] MOTOR S3 INICIALIZADO CORRECTAMENTE ---\n")

    def get_available_name(self, name, max_length=None):
        if getattr(self, '_is_local', False):
            return self._local_storage.get_available_name(name, max_length=max_length)
        return super().get_available_name(name, max_length=max_length)

    def url(self, name):
        if getattr(self, '_is_local', False):
            return self._local_storage.url(name)
        return super().url(name)
    
    def exists(self, name):
        if getattr(self, '_is_local', False):
            return self._local_storage.exists(name)
        return super().exists(name)
        
    def delete(self, name):
        if getattr(self, '_is_local', False):
            return self._local_storage.delete(name)
        return super().delete(name)

    def _save(self, name, content):
        # Si no tenemos credenciales, usar FileSystemStorage
        if getattr(self, '_is_local', False):
            print(f"\n--- [LOCAL DEBUG] GUARDANDO ARCHIVO LOCALMENTE ---")
            print(f"[LOCAL DEBUG] Nombre del archivo: {name}")
            print(f"[LOCAL DEBUG] Tipo de contenido: {type(content)}")
            
            try:
                # Usar FileSystemStorage interno para guardar localmente
                result = self._local_storage._save(name, content)
                print(f"[LOCAL DEBUG] ✓ ÉXITO: '{name}' guardado localmente en {settings.MEDIA_ROOT}")
                print(f"--- [LOCAL DEBUG] FIN DE LA OPERACIÓN ---\n")
                return result
            except Exception as e:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"[LOCAL DEBUG] ¡¡¡ERROR AL GUARDAR LOCALMENTE!!!")
                print(f"[LOCAL DEBUG] Tipo de Excepción: {type(e).__name__}")
                print(f"[LOCAL DEBUG] Mensaje de Error: {e}")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                raise
        
        # Si hay credenciales, usar S3
        print(f"\n--- [S3 DEBUG] INTENTANDO SUBIR EL ARCHIVO A S3 ---")
        print(f"[S3 DEBUG] Nombre del archivo: {name}")
        print(f"[S3 DEBUG] Tipo de contenido: {type(content)}")
        
        try:
            # Llamamos al método original para que haga la subida.
            result = super()._save(name, content)
            
            print(f"[S3 DEBUG] ¡ÉXITO! El archivo '{name}' fue subido a S3.")
            print(f"--- [S3 DEBUG] FIN DE LA OPERACIÓN DE SUBIDA ---\n")
            return result
            
        except Exception as e:
            # ¡LA CLAVE! Si algo falla durante la subida, lo capturaremos aquí.
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"[S3 DEBUG] ¡¡¡ERROR CATASTRÓFICO DURANTE LA SUBIDA A S3!!!")
            print(f"[S3 DEBUG] Tipo de Excepción: {type(e).__name__}")
            print(f"[S3 DEBUG] Mensaje de Error: {e}")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            raise