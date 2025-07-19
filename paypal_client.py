from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from django.conf import settings


class PayPalClient:
    def __init__(self):
        """
        Paypal sdk client setup
        """
        client_id = settings.PAYPAL_CLIENT_ID
        client_secret = settings.PAYPAL_CLIENT_SECRET
        mode = settings.PAYPAL_MODE

        if mode == "live":
            environment = LiveEnvironment(
                client_id=client_id, client_secret=client_secret
            )
        else:
            environment = SandboxEnvironment(
                client_id=client_id, client_secret=client_secret
            )

        self.client = PayPalHttpClient(environment=environment)
