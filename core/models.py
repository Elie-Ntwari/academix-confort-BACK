from django.db import models
from django.utils import timezone

class Salle(models.Model):
    """
    Model representing a room in the building.
    """
    nom = models.CharField(max_length=100, unique=True, help_text="Name of the room")
    description = models.TextField(blank=True, help_text="Optional description of the room")

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Salle"
        verbose_name_plural = "Salles"


class Mesure(models.Model):
    """
    Model representing an environmental measurement taken at a specific time.
    This is the raw event captured every X seconds/minutes.
    """
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, related_name='mesures', help_text="Room where the measurement was taken")
    temperature = models.FloatField(help_text="Temperature in °C")
    humidite = models.FloatField(help_text="Humidity in %")
    air = models.FloatField(help_text="Air quality in ppm (equivalent MQ-135)")
    bruit = models.FloatField(help_text="Noise level in dB")
    luminosite = models.FloatField(help_text="Light level in lux")
    timestamp = models.DateTimeField(default=timezone.now, help_text="Timestamp of the measurement")

    def __str__(self):
        return f"Mesure in {self.salle.nom} at {self.timestamp}"

    class Meta:
        verbose_name = "Mesure"
        verbose_name_plural = "Mesures"
        ordering = ['-timestamp']


class IndiceConfort(models.Model):
    """
    Model representing the comfort index calculated from a measurement.
    Linked to one measurement with a unique foreign key.
    """
    STATUT_CHOICES = [
        ('comfort', 'Confortable'),
        ('warning', 'Moyen'),
        ('danger', 'Inconfortable'),
    ]

    mesure = models.OneToOneField(Mesure, on_delete=models.CASCADE, related_name='indice_confort', help_text="Associated measurement")
    score_global = models.FloatField(help_text="Global comfort score (0-100)")
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, help_text="Comfort status")
    score_temperature = models.FloatField(help_text="Temperature score (0-100)")
    score_humidite = models.FloatField(help_text="Humidity score (0-100)")
    score_air = models.FloatField(help_text="Air quality score (0-100)")
    score_bruit = models.FloatField(help_text="Noise score (0-100)")
    score_luminosite = models.FloatField(help_text="Light score (0-100)")
    timestamp = models.DateTimeField(help_text="Timestamp copied from the measurement")

    def __str__(self):
        return f"Comfort Index for {self.mesure} - Score: {self.score_global}"

    class Meta:
        verbose_name = "Indice de Confort"
        verbose_name_plural = "Indices de Confort"
        ordering = ['-timestamp']


class Alerte(models.Model):
    """
    Model representing an alert generated based on measurement thresholds.
    """
    TYPE_CHOICES = [
        ('temperature', 'Température'),
        ('humidite', 'Humidité'),
        ('air', 'Qualité de l\'air'),
        ('bruit', 'Bruit'),
        ('luminosite', 'Luminosité'),
    ]

    NIVEAU_CHOICES = [
        ('warning', 'Avertissement'),
        ('danger', 'Danger'),
    ]

    mesure = models.ForeignKey(Mesure, on_delete=models.CASCADE, related_name='alertes', help_text="Associated measurement")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, help_text="Type of parameter that triggered the alert")
    valeur = models.FloatField(help_text="Measured value")
    seuil = models.FloatField(help_text="Threshold value")
    niveau = models.CharField(max_length=10, choices=NIVEAU_CHOICES, help_text="Alert level")
    message = models.TextField(help_text="Alert message")
    timestamp = models.DateTimeField(default=timezone.now, help_text="Timestamp of the alert")

    def __str__(self):
        return f"Alerte {self.type} - {self.niveau} in {self.mesure.salle.nom}"

    class Meta:
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"
        ordering = ['-timestamp']
