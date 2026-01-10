from rest_framework import serializers
from .models import Salle, Mesure, IndiceConfort, Alerte

class SalleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Salle model.
    """
    class Meta:
        model = Salle
        fields = '__all__'


class MesureSerializer(serializers.ModelSerializer):
    """
    Serializer for the Mesure model.
    Includes the salle name for readability.
    """
    salle_nom = serializers.CharField(source='salle.nom', read_only=True)

    class Meta:
        model = Mesure
        fields = '__all__'


class IndiceConfortSerializer(serializers.ModelSerializer):
    """
    Serializer for the IndiceConfort model.
    Includes salle and mesure details.
    """
    salle_nom = serializers.CharField(source='mesure.salle.nom', read_only=True)
    mesure_timestamp = serializers.DateTimeField(source='mesure.timestamp', read_only=True)

    class Meta:
        model = IndiceConfort
        fields = '__all__'


class AlerteSerializer(serializers.ModelSerializer):
    """
    Serializer for the Alerte model.
    Includes salle name.
    """
    salle_nom = serializers.CharField(source='mesure.salle.nom', read_only=True)

    class Meta:
        model = Alerte
        fields = '__all__'