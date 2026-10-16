from rest_framework import serializers


class HealthStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("ok", "unavailable"))
    application = serializers.ChoiceField(choices=("ok",))
    database = serializers.ChoiceField(choices=("ok", "unavailable"))
