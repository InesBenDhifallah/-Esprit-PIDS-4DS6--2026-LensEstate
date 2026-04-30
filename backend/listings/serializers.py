from rest_framework import serializers
from .models import Listing


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
    class Meta:
        model = Listing
        fields = '__all__'