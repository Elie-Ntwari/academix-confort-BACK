from django.urls import path
from . import views

urlpatterns = [
    # Collect a new measurement
    path('mesures/', views.collect_mesure, name='collect_mesure'),

    # List measurements
    path('mesures/list/', views.list_mesures, name='list_mesures'),

    # List comfort indices
    path('indices-confort/', views.list_indices_confort, name='list_indices_confort'),

    # List alerts
    path('alertes/', views.list_alertes, name='list_alertes'),

    # Get comfort statistics
    path('statistiques/', views.statistiques_confort, name='statistiques_confort'),

    # Get evolution data for charts
    path('evolution/', views.evolution_confort, name='evolution_confort'),
]