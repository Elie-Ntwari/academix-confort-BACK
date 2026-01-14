from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Salle, Mesure, IndiceConfort, Alerte
from .serializers import SalleSerializer, MesureSerializer, IndiceConfortSerializer, AlerteSerializer
from .services import collect_measurement, get_comfort_statistics, get_comfort_evolution

@api_view(['POST'])
def collect_mesure(request):
    """
    Endpoint: POST /api/mesures/
    Description: Collect a new environmental e measurement, automatically calculate comfort index and generate alerts.
    """
    try:
        response_data = collect_measurement(request.data)
        # Send real-time update via WebSocket
        channel_layer = get_channel_layer()
        salle_id = response_data['mesure']['salle']
        async_to_sync(channel_layer.group_send)(
            f'salle_{salle_id}',
            {
                'type': 'confort_message',
                'message': response_data
            }
        )
        return Response(response_data, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except ValidationError as e:
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_mesures(request):
    """
    Endpoint: GET /api/mesures/list/
    Description: List measurements, optionally filtered by salle_id, start_date, end_date.
    """
    salle_id = request.query_params.get('salle_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    mesures = Mesure.objects.all()

    if salle_id:
        mesures = mesures.filter(salle_id=salle_id)

    if start_date:
        mesures = mesures.filter(timestamp__gte=start_date)

    if end_date:
        mesures = mesures.filter(timestamp__lte=end_date)

    serializer = MesureSerializer(mesures, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_indices_confort(request):
    """
    Endpoint: GET /api/indices-confort/
    Description: List comfort indices, optionally filtered by salle_id, start_date, end_date.
    """
    salle_id = request.query_params.get('salle_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    indices = IndiceConfort.objects.select_related('mesure__salle')

    if salle_id:
        indices = indices.filter(mesure__salle_id=salle_id)

    if start_date:
        indices = indices.filter(timestamp__gte=start_date)

    if end_date:
        indices = indices.filter(timestamp__lte=end_date)

    serializer = IndiceConfortSerializer(indices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_alertes(request):
    """
    Endpoint: GET /api/alertes/
    Description: List alerts, optionally filtered by salle_id, type, niveau, start_date, end_date.
    """
    salle_id = request.query_params.get('salle_id')
    type_param = request.query_params.get('type')
    niveau = request.query_params.get('niveau')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    alertes = Alerte.objects.select_related('mesure__salle')

    if salle_id:
        alertes = alertes.filter(mesure__salle_id=salle_id)

    if type_param:
        alertes = alertes.filter(type=type_param)

    if niveau:
        alertes = alertes.filter(niveau=niveau)

    if start_date:
        alertes = alertes.filter(timestamp__gte=start_date)

    if end_date:
        alertes = alertes.filter(timestamp__lte=end_date)

    serializer = AlerteSerializer(alertes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def statistiques_confort(request):
    """
    Endpoint: GET /api/statistiques/
    Description: Get comfort statistics for a salle over a specified number of days (default 7).
    Requires salle_id query parameter.
    """
    salle_id = 1  # For testing purposes, default to salle_id 1
    # salle_id = request.query_params.get('salle_id')
    days = int(request.query_params.get('days', 7))  # Default to last 7 days

    try:
        response_data = get_comfort_statistics(salle_id, days)
        return Response(response_data)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def evolution_confort(request):
    """
    Endpoint: GET /api/evolution/
    Description: Get comfort evolution data for charts, from the first measurement to now, grouped by hour or day.
    Requires salle_id, optional period ('hour' or 'day').
    """
    salle_id = 1  # For testing purposes, default to salle_id 1
    # salle_id = request.query_params.get('salle_id')
    period = request.query_params.get('period', 'day')  # 'hour' or 'day'

    try:
        data = get_comfort_evolution(salle_id, period)
        return Response(data)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
