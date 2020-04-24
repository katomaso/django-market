from rest_framework import serializers
from rest_framework.utils.field_mapping import get_nested_relation_kwargs


class ModelSerializer(serializers.ModelSerializer):
    """Mixin to add django's REST serializer as 'serializer' fiels."""

    def contribute_to_class(self, model, name):
        """Setup "dynamically" model class for this serializer."""
        cls = self.__class__
        setattr(cls.Meta, "model", model)
        # recursively fill in model class
        if hasattr(cls.Meta, "list_serializer_class"):
            setattr(cls.Meta.list_serializer_class.Meta, "model", model)
        setattr(model, name, cls)

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """Create nested fields for forward and reverse relationships."""
        class NestedSerializer(ModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = '__all__'
        field_class = NestedSerializer

        if hasattr(relation_info.related_model, "serializer"):
            if hasattr(relation_info.related_model.serializer, "fields"):
                field_class.Meta.fields = relation_info.related_model.serializer.Meta.fields
        field_kwargs = get_nested_relation_kwargs(relation_info)
        return field_class, field_kwargs


class UserListSerializer(ModelSerializer):
    """Serialize User for lists with less details."""

    class Meta:
        """Serializer options."""
        fields = ('id', 'name', 'slug', 'date_joined')
        depth = 0


class UserSerializer(ModelSerializer):
    """Serialize User for list-view."""

    class Meta:
        """Serializer options."""
        list_serializer_class = UserListSerializer
        fields = ('id', 'name', 'slug', 'date_joined')
        depth = 0


class ProductSerializer(ModelSerializer):
    """Product serialization goes deeper because we want Offers with it."""

    class Meta:
        """Serializer options."""
        fields = ('id', 'name', 'slug', 'active', 'price', 'description', 'tax',
                  'manufacturer', 'offer_set', 'comments')
        depth = 2


class CategorySerializer(ModelSerializer):
    """Category is simple to serialize."""

    class Meta:
        """Serializer options."""
        fields = ('name', 'slug', )
        depth = 0


class OfferSerializer(ModelSerializer):
    """Offer serialization includes Vendor as well."""

    class Meta:
        """Serializer options."""
        fields = ('id', 'name', 'slug', 'unit_price', 'unit_quantity',
                  'unit_measure', 'vendor')
        depth = 1


class VendorSerializer(ModelSerializer):
    """Vendor serializes some computed properties like "pays_tax"."""

    class Meta:
        """Serializer options."""
        depth = 0
        fields = ('id', 'name', 'slug', 'motto', 'active', 'created', 'ships',
                  'pays_tax')
