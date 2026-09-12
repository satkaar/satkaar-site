from django.apps import AppConfig


class MesureConfig(AppConfig):
    name = 'mesure'
    verbose_name = 'Mesure d’audience'

    def ready(self):
        from . import signals  # noqa: F401
