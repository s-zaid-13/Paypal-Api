from rest_framework import serializers
from .models import User


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_subscribed"]
