from django.apps import AppConfig


class UrbanismeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'urbanisme'
    verbose_name = 'Urbanisme & Projets'

    def ready(self):
        import urbanisme.signals  # noqa: F401
