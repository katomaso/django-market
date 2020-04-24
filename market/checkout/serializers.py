from market.core import serializers


class CartSerializer(serializers.ModelSerializer):
    """Dive into its items."""

    class Meta:
        """Serializer options."""
        depth = 1
        fields = ('created', 'modified', 'items')


class CartItemSerializer(serializers.ModelSerializer):
    """Serialize everything but back-reference to Cart."""

    class Meta:
        """Serializer options."""
        depth = 0
        fields = ('quantity', 'item')
