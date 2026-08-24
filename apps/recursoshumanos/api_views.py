# recursoshumanos/api_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import TareoDiario, Trabajador, ConfiguracionTolerancia
from .serializers import ConfiguracionToleranciaSerializer
from .services import actualizar_tolerancia, crear_o_actualizar_tolerancia, listar_tolerancias


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


# ==============================================================================
# HU-06 (CAV-15) - CAV-71: ENDPOINTS API PARA CONFIGURACIÓN DE TOLERANCIA
# ==============================================================================

class EsRRHHoGerencia(BasePermission):
    """Restringe el acceso a los mismos grupos que usa group_required en las vistas HTML."""
    grupos_permitidos = {"Recursos Humanos", "Gerencia", "Administracion"}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=self.grupos_permitidos).exists()


class ConfiguracionToleranciaListCreateView(APIView):
    """
    GET: lista las configuraciones de tolerancia (filtrable por ?sede=<id>).
    POST: crea (o actualiza si ya existe) la tolerancia de una sede/horario.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [EsRRHHoGerencia]

    def get(self, request):
        sede_id = request.query_params.get('sede')
        configuraciones = listar_tolerancias(sede_id=sede_id)
        serializer = ConfiguracionToleranciaSerializer(configuraciones, many=True)
        return Response(serializer.data)

    def post(self, request):
        sede_id = request.data.get('sede')
        tipo_horario = request.data.get('tipo_horario')
        minutos = request.data.get('minutos_tolerancia')

        if not sede_id or not tipo_horario or minutos is None:
            return Response(
                {'detail': 'sede, tipo_horario y minutos_tolerancia son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConfiguracionToleranciaSerializer(data={
            'sede': sede_id,
            'tipo_horario': tipo_horario,
            'minutos_tolerancia': minutos,
        })
        serializer.is_valid(raise_exception=True)

        configuracion = crear_o_actualizar_tolerancia(
            sede_id=sede_id,
            tipo_horario=tipo_horario,
            minutos_tolerancia=serializer.validated_data['minutos_tolerancia'],
            usuario=request.user,
        )
        return Response(
            ConfiguracionToleranciaSerializer(configuracion).data,
            status=status.HTTP_201_CREATED,
        )


class ConfiguracionToleranciaDetailView(APIView):
    """GET: detalle. PUT/PATCH: actualiza los minutos de tolerancia (con auditoría)."""
    authentication_classes = [SessionAuthentication]
    permission_classes = [EsRRHHoGerencia]

    def get_object(self, pk):
        return get_object_or_404(ConfiguracionTolerancia, pk=pk)

    def get(self, request, pk):
        return Response(ConfiguracionToleranciaSerializer(self.get_object(pk)).data)

    def put(self, request, pk):
        return self._actualizar(request, pk)

    def patch(self, request, pk):
        return self._actualizar(request, pk)

    def _actualizar(self, request, pk):
        configuracion = self.get_object(pk)
        minutos = request.data.get('minutos_tolerancia')

        if minutos is None:
            return Response(
                {'detail': 'minutos_tolerancia es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConfiguracionToleranciaSerializer(
            configuracion, data={'minutos_tolerancia': minutos}, partial=True
        )
        serializer.is_valid(raise_exception=True)

        configuracion_actualizada = actualizar_tolerancia(
            configuracion_id=configuracion.pk,
            minutos_nuevos=serializer.validated_data['minutos_tolerancia'],
            usuario=request.user,
        )
        return Response(ConfiguracionToleranciaSerializer(configuracion_actualizada).data)