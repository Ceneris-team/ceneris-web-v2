# recursoshumanos/api_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.utils import timezone
from .models import TareoDiario, Trabajador


TARDANZA_MINIMA_HORAS = Decimal('0.25')

class HistorialAsistenciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            trabajador = Trabajador.objects.get(user=request.user)
        except Trabajador.DoesNotExist:
            return Response({"error": "Usuario no es trabajador"}, status=400)

        hoy = timezone.localtime()
        # Obtenemos mes y año de los parámetros GET (ej: ?mes=11&anio=2025)
        mes = int(request.query_params.get('mes', hoy.month))
        anio = int(request.query_params.get('anio', hoy.year))

        tareos = TareoDiario.objects.filter(
            trabajador=trabajador,
            fecha__year=anio,
            fecha__month=mes
        ).select_related('justificacion') # Si tienes relación con justificación

        data = []
        for t in tareos:
            # Verificar si tiene justificación
            just_estado = None
            # Asegúrate que la relación en tu modelo TareoDiario o Justificacion exista
            if hasattr(t, 'justificacion'):
                just_estado = t.justificacion.estado_solicitud

            item = {
                "fecha": t.fecha.strftime('%Y-%m-%d'),
                "resultado": t.resultado,
                "estado_planificado": t.estado,
                "entrada_prog": t.hora_entrada.strftime('%H:%M') if t.hora_entrada else "--:--",
                "salida_prog": t.hora_salida.strftime('%H:%M') if t.hora_salida else "--:--",
                "entrada_real": t.hora_entrada_real.strftime('%H:%M') if t.hora_entrada_real else None,
                "salida_real": t.hora_salida_real.strftime('%H:%M') if t.hora_salida_real else None,
                "tardanza_horas": str(t.horas_tardanza) if t.horas_tardanza and t.horas_tardanza >= TARDANZA_MINIMA_HORAS else "0.00",
                "justificacion_estado": just_estado
            }
            data.append(item)

        return Response(data)