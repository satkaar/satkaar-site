from django.apps import AppConfig


class CourrielConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "courriel"
    verbose_name = "Mail"

    def ready(self):
        from . import signals  # noqa: F401
