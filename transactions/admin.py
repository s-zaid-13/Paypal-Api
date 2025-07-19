from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "payer_email",
        "amount",
        "currency",
        "status",
        "transaction_type",
        "ip_address",
        "capture_id",
        # "product",
        "created_at",
    )
    search_fields = ("transaction_id", "payer_email")
    list_filter = ("transaction_type", "created_at")
