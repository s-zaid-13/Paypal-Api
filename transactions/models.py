from django.db import models
from .utils import TRANSACTION_TYPES, STATUS_CHOICES
from products.models import Product
from accounts.models import User


class Transaction(models.Model):
    transaction_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    payer_name = models.CharField(max_length=255)
    payer_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")
    created_at = models.DateTimeField(auto_now_add=True)
    capture_id = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.payer_email} - {self.amount}"
