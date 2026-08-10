"""
Backend de Email con OAuth2 para Microsoft 365
Usa MSAL (Microsoft Authentication Library) para obtener tokens de acceso
"""
import base64
import msal
import os
from django.core.mail.backends.smtp import EmailBackend
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


class OAuth2EmailBackend(EmailBackend):
    """
    Backend de email que usa OAuth2 con Azure AD para Microsoft 365
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Credenciales OAuth2 desde variables de entorno
        self.client_id = os.environ.get('AZURE_CLIENT_ID')
        self.tenant_id = os.environ.get('AZURE_TENANT_ID')
        self.client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        self.user_email = os.environ.get('EMAIL_HOST_USER', 'notificaciones@ceneris.com')
        
    def get_access_token(self):
        """
        Obtiene un token de acceso usando las credenciales de Azure AD
        """
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret
        )
        
        # Scope correcto para SMTP con OAuth2
        scopes = [f"https://outlook.office365.com/.default"]
        result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"Error obteniendo token: {result.get('error_description', 'Unknown error')}")
    
    def open(self):
        """
        Abre conexión SMTP con autenticación OAuth2
        """
        if self.connection:
            return False
            
        try:
            self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            self.connection.ehlo()
            
            if self.use_tls:
                self.connection.starttls()
                self.connection.ehlo()
            
            # Autenticación OAuth2
            access_token = self.get_access_token()
            auth_string = f"user={self.user_email}\x01auth=Bearer {access_token}\x01\x01"
            auth_string = base64.b64encode(auth_string.encode()).decode()
            
            self.connection.docmd('AUTH', 'XOAUTH2 ' + auth_string)
            
            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            return False
