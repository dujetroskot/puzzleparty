from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class GamesCoreConfig(AppConfig):
    name = "games.core"
    label = "games_core"

    def ready(self):
        # Importa game.py iz svakog appa u INSTALLED_APPS,
        # čime se sve igre same registriraju.
        autodiscover_modules("game")