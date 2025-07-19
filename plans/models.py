from django.db import models


INTERVAL_CHOICES = (
    ("MONTH", "Monthly"),
    ("YEAR", "Yearly"),
)


class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_interval = models.CharField(
        max_length=10, choices=INTERVAL_CHOICES, default="MONTH"
    )
    paypal_plan_id = models.CharField(
        max_length=255, help_text="PayPal Plan ID from PayPal dashboard or SDK"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
