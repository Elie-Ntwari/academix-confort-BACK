"""
Service layer for core business logic.
Handles measurement collection, statistics calculation, and data retrieval.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Max, Min, Count, Subquery, OuterRef
from rest_framework.exceptions import ValidationError
from .models import Salle, Mesure, IndiceConfort, Alerte
from .serializers import MesureSerializer, IndiceConfortSerializer, AlerteSerializer
from .utils import calculate_parameter_score, calculate_global_score, determine_status, generate_alerts
from django.db.models.functions import TruncHour, TruncDay

def collect_measurement(data):
    """
    Service to collect a new environmental measurement.
    Validates data, creates measurement, calculates comfort index, and generates alerts.
    Returns a dictionary with serialized mesure, indice_confort, and alertes.
    Raises ValidationError or ValueError on invalid data.
    """
    salle_id = data.get('salle_id', 1)  # Default to 1 if not provided
    if not salle_id:
        raise ValueError('salle_id is required')

    salle = get_object_or_404(Salle, id=salle_id)

    mesure_data = {
        'salle': salle.id,
        'temperature': data.get('temperature'),
        'humidite': data.get('humidite'),
        'air': data.get('air'),
        'bruit': data.get('bruit'),
        'luminosite': data.get('luminosite'),
        'timestamp': data.get('timestamp', timezone.now()),
    }

    mesure_serializer = MesureSerializer(data=mesure_data)
    if not mesure_serializer.is_valid():
        raise ValidationError(mesure_serializer.errors)

    with transaction.atomic():
        mesure = mesure_serializer.save()

        # Calculate scores
        scores = {
            'temperature': calculate_parameter_score(mesure.temperature, 'temperature'),
            'humidite': calculate_parameter_score(mesure.humidite, 'humidite'),
            'air': calculate_parameter_score(mesure.air, 'air'),
            'bruit': calculate_parameter_score(mesure.bruit, 'bruit'),
            'luminosite': calculate_parameter_score(mesure.luminosite, 'luminosite'),
        }

        global_score = calculate_global_score(scores)
        statut = determine_status(global_score)

        # Create comfort index
        indice_data = {
            'mesure': mesure.id,
            'score_global': global_score,
            'statut': statut,
            'score_temperature': scores['temperature'],
            'score_humidite': scores['humidite'],
            'score_air': scores['air'],
            'score_bruit': scores['bruit'],
            'score_luminosite': scores['luminosite'],
            'timestamp': mesure.timestamp,
        }

        indice_serializer = IndiceConfortSerializer(data=indice_data)
        if not indice_serializer.is_valid():
            raise ValidationError(indice_serializer.errors)
        indice = indice_serializer.save()

        # Generate alerts
        alerts_data = generate_alerts(mesure, scores)
        created_alerts = []
        for alert_data in alerts_data:
            alert_data['mesure'] = mesure.id
            alert_serializer = AlerteSerializer(data=alert_data)
            if alert_serializer.is_valid():
                alert_serializer.save()
                created_alerts.append(alert_serializer.data)

    return {
        
        'mesure': mesure_serializer.data,
        'indice_confort': indice_serializer.data,
        'alertes': created_alerts,
    }


def get_comfort_statistics(salle_id, days):
    """
    Service to calculate comfort statistics for a salle over a given number of days.
    Returns a dictionary with stats, status distribution, discomfort percentage, and alert count.
    Raises ValueError if salle_id is invalid.
    """
    if not salle_id:
        raise ValueError('salle_id is required')

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    indices = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )

    stats = indices.aggregate(
        avg_score=Avg('score_global'),
        max_score=Max('score_global'),
        min_score=Min('score_global'),
        count=Count('id')
    )

    # Count by status
    status_counts = indices.values('statut').annotate(count=Count('statut'))

    # Time spent in discomfort
    discomfort_count = indices.filter(statut__in=['warning', 'danger']).count()
    total_count = indices.count()
    discomfort_percentage = (discomfort_count / total_count * 100) if total_count > 0 else 0

    # Number of alerts
    alert_count = Alerte.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).count()

    return {
        'period_days': days,
        'average_score': stats['avg_score'],
        'max_score': stats['max_score'],
        'min_score': stats['min_score'],
        'total_measurements': stats['count'],
        'status_distribution': list(status_counts),
        'discomfort_percentage': discomfort_percentage,
        'alert_count': alert_count,
    }


def get_comfort_evolution(salle_id, period):
    """
    Service to get comfort evolution data for charts, from the first measurement to now, grouped by hour or day.
    Returns a list of dictionaries with min, max, avg, and current for global score and each parameter score.
    Raises ValueError if salle_id is invalid.
    """
    if not salle_id:
        raise ValueError("salle_id is required")

    earliest = IndiceConfort.objects.filter(mesure__salle_id=salle_id).aggregate(min_ts=Min('timestamp'))['min_ts']
    if not earliest:
        return []

    start_date = earliest
    end_date = timezone.now()

    queryset = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )

    if period == "hour":
        trunc_func = TruncHour
        delta = timedelta(hours=1)
    else:
        trunc_func = TruncDay
        delta = timedelta(days=1)

    # Subqueries for current values (latest in each period)
    current_score_global_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_global')[:1]

    current_score_temp_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_temperature')[:1]

    current_score_hum_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_humidite')[:1]

    current_score_air_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_air')[:1]

    current_score_bruit_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_bruit')[:1]

    current_score_lum_sub = IndiceConfort.objects.filter(
        mesure__salle_id=salle_id,
        timestamp__gte=OuterRef('period'),
        timestamp__lt=OuterRef('period') + delta
    ).order_by('-timestamp').values('score_luminosite')[:1]

    data = (
        queryset
        .annotate(period=trunc_func("timestamp"))
        .values("period")
        .annotate(
            min_score_global=Min("score_global"),
            max_score_global=Max("score_global"),
            avg_score_global=Avg("score_global"),
            current_score_global=Subquery(current_score_global_sub),
            min_score_temp=Min("score_temperature"),
            max_score_temp=Max("score_temperature"),
            avg_score_temp=Avg("score_temperature"),
            current_score_temp=Subquery(current_score_temp_sub),
            min_score_hum=Min("score_humidite"),
            max_score_hum=Max("score_humidite"),
            avg_score_hum=Avg("score_humidite"),
            current_score_hum=Subquery(current_score_hum_sub),
            min_score_air=Min("score_air"),
            max_score_air=Max("score_air"),
            avg_score_air=Avg("score_air"),
            current_score_air=Subquery(current_score_air_sub),
            min_score_bruit=Min("score_bruit"),
            max_score_bruit=Max("score_bruit"),
            avg_score_bruit=Avg("score_bruit"),
            current_score_bruit=Subquery(current_score_bruit_sub),
            min_score_lum=Min("score_luminosite"),
            max_score_lum=Max("score_luminosite"),
            avg_score_lum=Avg("score_luminosite"),
            current_score_lum=Subquery(current_score_lum_sub),
        )
        .order_by("period")
    )

    return list(data)
