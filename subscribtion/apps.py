from django.apps import AppConfig

class SubscribtionConfig(AppConfig):
    name = 'subscribtion'
    
    def ready(self):
        """
        Connect signals when the app is ready.
        This ensures our signal handlers are registered properly.
        """
        # Import signals to register them
        import subscribtion.signals