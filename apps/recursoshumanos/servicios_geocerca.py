"""Validacion de geocerca en el servidor para las marcaciones de la app movil.

Contexto de por que existe este modulo:

Hasta ahora la geocerca era 100% del lado del cliente. El backend enviaba las
zonas al celular (`ubicaciones_permitidas`) y guardaba la lat/lon que el celular
devolvia, pero NUNCA las comparaba. Cualquiera con un JWT valido -- un APK
modificado, o directamente `curl` -- podia registrar asistencia desde cualquier
punto del planeta y el servidor lo aceptaba con 201. Ver
`api/test_geocerca.py`.

POLITICA: se OBSERVA, no se rechaza.

En faena el GPS deriva, entra en ahorro de bateria, se queda con la ultima
posicion conocida o simplemente no fija bajo techo metalico. Responder 403 a una
marca fuera de radio haria perder planilla real de trabajadores que si
estuvieron. Asi que la marca se guarda SIEMPRE y se etiqueta; RRHH decide.
"""

from math import asin, cos, radians, sin, sqrt

from django.conf import settings

# Radio medio de la Tierra (IUGG), en metros.
RADIO_TIERRA_M = 6371008.8

# Holgura extra sobre el `radio` de la zona, para absorber el error tipico del
# GPS de un celular de gama media a cielo abierto (20-50 m; peor bajo techo).
# Sin ella, una zona de radio ajustado generaria observaciones constantes de
# gente que si estaba dentro, y el ruido volveria inutil la revision de RRHH.
# Ponerla en 0 en settings deja al `radio` de cada Ubicacion como unico criterio.
MARGEN_GPS_METROS = getattr(settings, 'GEOCERCA_MARGEN_GPS_METROS', 50)


def distancia_metros(lat1, lon1, lat2, lon2):
    """Distancia haversine entre dos puntos, en metros.

    Haversine y no una proyeccion plana porque las zonas pueden estar en
    cualquier latitud del pais y el costo de calcularlo bien es nulo.
    """
    lat1, lon1, lat2, lon2 = map(radians, (float(lat1), float(lon1), float(lat2), float(lon2)))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * RADIO_TIERRA_M * asin(sqrt(a))


def evaluar_geocerca(trabajador, latitud, longitud, margen_m=None):
    """Evalua una marcacion contra las zonas permitidas del trabajador.

    Devuelve `(estado, ubicacion_mas_cercana, distancia_m)` donde `estado` es
    uno de los `Asistencia.GEOCERCA_*` y `distancia_m` es la distancia al
    CENTRO de la zona mas cercana (entero, metros) o None si no se pudo medir.

    La zona reportada es siempre la mas cercana de las permitidas, tambien
    cuando la marca queda fuera: es el dato que RRHH necesita para juzgar si
    fue deriva de GPS (a 80 m de la puerta) o una marca desde otra ciudad.
    """
    # Import local: el modelo importa indirectamente este modulo en las vistas,
    # y a nivel de modulo esto seria un ciclo.
    from .models import Asistencia

    if margen_m is None:
        margen_m = MARGEN_GPS_METROS

    if latitud is None or longitud is None:
        return Asistencia.GEOCERCA_SIN_COORDENADAS, None, None

    zonas = list(trabajador.ubicaciones_permitidas.all())
    if not zonas:
        # El trabajador no tiene zonas asignadas. No es culpa suya ni evidencia
        # de nada: es un dato de configuracion que RRHH no cargo. Se distingue
        # de FUERA para que no se confunda un vacio administrativo con una
        # marca sospechosa.
        return Asistencia.GEOCERCA_SIN_ZONAS, None, None

    mejor_zona = None
    mejor_distancia = None
    dentro = False

    for zona in zonas:
        d = distancia_metros(latitud, longitud, zona.latitud, zona.longitud)
        if mejor_distancia is None or d < mejor_distancia:
            mejor_distancia = d
            mejor_zona = zona
        if d <= (zona.radio or 0) + margen_m:
            dentro = True
            # La zona que valida la marca es la que la contiene, aunque otra
            # quede marginalmente mas cerca del centro.
            mejor_zona = zona
            mejor_distancia = d
            break

    estado = Asistencia.GEOCERCA_DENTRO if dentro else Asistencia.GEOCERCA_FUERA
    return estado, mejor_zona, int(round(mejor_distancia))
