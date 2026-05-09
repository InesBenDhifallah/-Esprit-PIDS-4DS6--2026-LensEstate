from rest_framework import serializers
from .models import Listing

# Lazy imports to avoid circular dependencies and slow startup
def get_predictions_service():
    from predictions.services import predict_price
    return predict_price

def get_forecasting_service():
    from forcasting.forcasting import get_region_payload
    return get_region_payload


class ListingCardSerializer(serializers.ModelSerializer):
    """Light version — used for listing cards and map pins."""
    class Meta:
        model = Listing
        fields = [
            'id', 'listing_id', 'title', 'property_type',
            'transaction_type', 'price', 'currency',
            'surface_m2', 'rooms', 'bedrooms', 'bathrooms',
            'governorate', 'city', 'latitude', 'longitude',
            'image_urls', 'has_images', 'is_agency',
        ]


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full version — used for the single listing page."""
    ai_insights = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = '__all__'

    def get_ai_insights(self, obj):
        # 1. Prepare data for prediction
        listing_data = {
            'surface_m2': obj.surface_m2 or 0,
            'rooms': obj.rooms or 0,
            'bedrooms': obj.bedrooms or 0,
            'bathrooms': obj.bathrooms or 0,
            'property_type': obj.property_type,
            'seller_type': obj.seller_type,
            'governorate': obj.governorate,
            'city': obj.city,
            'description': obj.description,
            'image_count': obj.image_count or 0,
            'has_pool': obj.has_pool,
            'has_parking': obj.has_parking,
            'has_garden': obj.has_garden,
            'has_elevator': obj.has_elevator,
            'has_air_conditioning': obj.has_air_conditioning,
            'has_heating': obj.has_heating,
            'has_security': obj.has_security,
            'has_furniture': obj.has_furniture,
            'has_terrace': obj.has_terrace,
            'has_sea_view': obj.has_sea_view,
            'has_basement': obj.has_basement,
            'has_standing': obj.has_standing,
        }

        # 2. Get prediction & confidence
        try:
            predict_price = get_predictions_service()
            prediction = predict_price(listing_data)
            predicted_price = prediction.get('price')
            confidence = prediction.get('conf', 75)
        except Exception as e:
            print(f"Prediction failed: {e}")
            predicted_price = obj.predicted_price
            confidence = 70

        # 3. Get trend
        try:
            get_region_payload = get_forecasting_service()
            forecast = get_region_payload(obj.governorate)
            trend = forecast.get('projected_growth_pct', 0)
        except Exception as e:
            print(f"Forecasting failed: {e}")
            trend = 0

        return {
            'predicted_price': predicted_price,
            'confidence': confidence,
            'trend': trend
        }