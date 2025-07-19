from rest_framework import serializers


class CreateSubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.CharField()


class ReviseSubscriptionSerializer(serializers.Serializer):
    subscription_id = serializers.CharField()
    new_plan_id = serializers.CharField()
