"""Constantes de l'intégration NRJ Mobile."""
from datetime import timedelta

DOMAIN = "nrjmobile"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Conso mise à jour lentement côté opérateur ; token ~5 min -> on ré-auth à chaque cycle.
SCAN_INTERVAL = timedelta(minutes=30)
