from rest_framework import serializers

from .catalogue import validate_option
from .models import Country, Locality, Option, Subdivision


class CatalogueCodeField(serializers.CharField):
    def __init__(self, category, **kwargs):
        self.category = category
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        code = super().to_internal_value(data)
        return validate_option(self.category, code, self.field_name)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "code", "name"]


class SubdivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subdivision
        fields = ["id", "country_id", "code", "name"]


class LocalitySerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Locality
        fields = ["id", "country_id", "subdivision_id", "name", "label"]


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["category", "code", "label"]


class ReferenceQuery(serializers.Serializer):
    q = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country_id = serializers.IntegerField(min_value=1, required=False)
    subdivision_id = serializers.IntegerField(min_value=1, required=False)
    category = serializers.CharField(max_length=40, required=False)
    page = serializers.IntegerField(min_value=1, required=False)


class ReferencePageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField(child=serializers.DictField())
