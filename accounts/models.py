from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_subscribed = models.BooleanField(default=False)
    paypal_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    subscription_pending = models.BooleanField(default=False)
    paypal_plan_id = models.CharField(max_length=255, null=True, blank=True)
    trial_ip = models.GenericIPAddressField(null=True, blank=True)
