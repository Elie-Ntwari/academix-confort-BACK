"""
Utility functions for calculating comfort scores and generating alerts.
"""

# Thresholds for comfort zones
THRESHOLDS = {
    'temperature': {'min': 22, 'max': 26},
    'humidite': {'min': 40, 'max': 60},
    'bruit': {'max': 60},
    'luminosite': {'min': 300, 'max': 500},
    'air': {'max': 1000},
}

# Weights for global score calculation
WEIGHTS = {
    'temperature': 0.25,
    'humidite': 0.20,
    'air': 0.25,
    'bruit': 0.20,
    'luminosite': 0.10,
}

def calculate_parameter_score(value, param):
    """
    Calculate the score for a single parameter (0-100).
    If within comfortable range, score = 100.
    Otherwise, score = max(0, 100 - (deviation * 10))
    """
    thresh = THRESHOLDS[param]
    if 'min' in thresh and 'max' in thresh:
        # Range-based
        if thresh['min'] <= value <= thresh['max']:
            return 100.0
        else:
            # Find the closest boundary
            if value < thresh['min']:
                deviation = thresh['min'] - value
            else:
                deviation = value - thresh['max']
            return max(0.0, 100.0 - (deviation * 10))
    elif 'max' in thresh:
        # Upper limit only
        if value <= thresh['max']:
            return 100.0
        else:
            deviation = value - thresh['max']
            return max(0.0, 100.0 - (deviation * 10))
    elif 'min' in thresh:
        # Lower limit only
        if value >= thresh['min']:
            return 100.0
        else:
            deviation = thresh['min'] - value
            return max(0.0, 100.0 - (deviation * 10))
    return 0.0

def calculate_global_score(scores):
    """
    Calculate the weighted global comfort score.
    """
    return (
        scores['temperature'] * WEIGHTS['temperature'] +
        scores['humidite'] * WEIGHTS['humidite'] +
        scores['air'] * WEIGHTS['air'] +
        scores['bruit'] * WEIGHTS['bruit'] +
        scores['luminosite'] * WEIGHTS['luminosite']
    )

def determine_status(global_score):
    """
    Determine the comfort status based on global score.
    """
    if global_score >= 70:
        return 'comfort'
    elif global_score >= 40:
        return 'warning'
    else:
        return 'danger'

def generate_alerts(mesure, scores):
    """
    Generate alerts if any parameter is out of range.
    Returns a list of alert dictionaries.
    """
    alerts = []
    params = {
        'temperature': mesure.temperature,
        'humidite': mesure.humidite,
        'air': mesure.air,
        'bruit': mesure.bruit,
        'luminosite': mesure.luminosite,
    }

    for param, value in params.items():
        thresh = THRESHOLDS[param]
        is_out = False
        niveau = None
        seuil = None

        if 'min' in thresh and 'max' in thresh:
            if value < thresh['min']:
                is_out = True
                seuil = thresh['min']
                niveau = 'warning' if value >= thresh['min'] - 5 else 'danger'
            elif value > thresh['max']:
                is_out = True
                seuil = thresh['max']
                niveau = 'warning' if value <= thresh['max'] + 5 else 'danger'
        elif 'max' in thresh:
            if value > thresh['max']:
                is_out = True
                seuil = thresh['max']
                niveau = 'warning' if value <= thresh['max'] + 10 else 'danger'
        elif 'min' in thresh:
            if value < thresh['min']:
                is_out = True
                seuil = thresh['min']
                niveau = 'warning' if value >= thresh['min'] - 10 else 'danger'

        if is_out:
            message = f"Valeur {param} ({value}) hors seuil ({seuil})"
            alerts.append({
                'type': param,
                'valeur': value,
                'seuil': seuil,
                'niveau': niveau,
                'message': message,
            })

    return alerts