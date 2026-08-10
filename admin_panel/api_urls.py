# api_urls.py (NUEVO ARCHIVO)

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

# ¡Importa la vista de API que creamos en recursoshumanos!
from recursoshumanos.views import SolicitudHorasExtraCreateAPIView

urlpatterns = [
    # 1. Endpoint para que la app se autentique y obtenga un token
    #    La app llamará a: /api/token/
    path('token/', obtain_auth_token, name='api_token_auth'),

    # 2. Endpoint para que la app cree una nueva solicitud de horas extra
    #    La app llamará a: /api/horas-extra/solicitar/
    path('horas-extra/solicitar/', SolicitudHorasExtraCreateAPIView.as_view(), name='api_solicitar_he'),
]