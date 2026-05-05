from rest_framework import serializers


class PredictRequestSerializer(serializers.Serializer):
    region = serializers.CharField(max_length=120)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    property_type = serializers.CharField(max_length=60)
    seller_type = serializers.CharField(max_length=60)
    surface_m2 = serializers.FloatField(min_value=10, max_value=10000)
    rooms = serializers.FloatField(min_value=0, max_value=42)
    bedrooms = serializers.FloatField(min_value=0, max_value=20)
    bathrooms = serializers.FloatField(min_value=0, max_value=15)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    image_count = serializers.IntegerField(required=False, min_value=0, max_value=30, default=0)

    has_pool = serializers.BooleanField(required=False, default=False)
    has_parking = serializers.BooleanField(required=False, default=False)
    has_garden = serializers.BooleanField(required=False, default=False)
    has_elevator = serializers.BooleanField(required=False, default=False)
    has_air_conditioning = serializers.BooleanField(required=False, default=False)
    has_heating = serializers.BooleanField(required=False, default=False)
    has_security = serializers.BooleanField(required=False, default=False)
    has_furniture = serializers.BooleanField(required=False, default=False)
    has_terrace = serializers.BooleanField(required=False, default=False)
    has_sea_view = serializers.BooleanField(required=False, default=False)
    has_basement = serializers.BooleanField(required=False, default=False)
    has_standing = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        city = attrs.get("city", "").strip()
        if not city:
            attrs["city"] = attrs["region"]

        attrs["property_type"] = str(attrs["property_type"]).strip().lower()
        attrs["seller_type"] = str(attrs["seller_type"]).strip().lower()
        return attrs
