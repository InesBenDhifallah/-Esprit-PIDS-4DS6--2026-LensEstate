from django.apps import AppConfig
import os

class PredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictions'

    def ready(self):
        # On évite de charger deux fois avec le reloader de Django
        if os.environ.get('RUN_MAIN') == 'true':
            from .services import load_all_models
            import threading
            # On lance le chargement dans un thread séparé pour ne pas bloquer le démarrage du serveur
            # tout en préparant les modèles pour la première requête
            threading.Thread(target=load_all_models, daemon=True).start()
