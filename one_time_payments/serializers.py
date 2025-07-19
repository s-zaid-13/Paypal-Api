from rest_framework import serializers


class ProductOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    items = ProductOrderItemSerializer(many=True)
    currency = serializers.CharField()
