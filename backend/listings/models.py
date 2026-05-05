from django.db import models


class Listing(models.Model):

    # ── identifiers ──
    listing_id   = models.CharField(max_length=100, unique=True)
    listing_url  = models.URLField(max_length=500, blank=True)
    source       = models.CharField(max_length=100, blank=True)

    # ── core info ──
    title            = models.CharField(max_length=500)
    property_type    = models.CharField(max_length=100, blank=True)
    transaction_type = models.CharField(max_length=50, blank=True)
    price            = models.FloatField(null=True, blank=True)
    currency         = models.CharField(max_length=10, default='TND')
    surface_m2       = models.FloatField(null=True, blank=True)
    rooms            = models.FloatField(null=True, blank=True)
    bedrooms         = models.FloatField(null=True, blank=True)
    bathrooms        = models.FloatField(null=True, blank=True)

    # ── location ──
    country     = models.CharField(max_length=100, default='Tunisia')
    governorate = models.CharField(max_length=100, blank=True)
    city        = models.CharField(max_length=100, blank=True)
    latitude    = models.FloatField(null=True, blank=True)
    longitude   = models.FloatField(null=True, blank=True)

    # ── description ──
    description            = models.TextField(blank=True)
    description_word_count = models.IntegerField(default=0)

    # ── images ──
    image_count = models.IntegerField(default=0)
    image_urls  = models.JSONField(default=list, blank=True)
    has_images  = models.BooleanField(default=False)

    # ── seller ──
    seller_type = models.CharField(max_length=50, blank=True)
    is_agency   = models.BooleanField(default=False)

    # ── amenities ──
    has_elevator         = models.BooleanField(default=False)
    has_basement         = models.BooleanField(default=False)
    has_heating          = models.BooleanField(default=False)
    has_air_conditioning = models.BooleanField(default=False)
    has_garden           = models.BooleanField(default=False)
    has_furniture        = models.BooleanField(default=False)
    has_parking          = models.BooleanField(default=False)
    has_pool             = models.BooleanField(default=False)
    has_security         = models.BooleanField(default=False)
    has_standing         = models.BooleanField(default=False)
    has_terrace          = models.BooleanField(default=False)
    has_sea_view         = models.BooleanField(default=False)

    # ── data quality flags ──
    is_price_imputed   = models.BooleanField(default=False)
    has_surface        = models.BooleanField(default=False)
    has_rooms_info     = models.BooleanField(default=False)
    has_bathrooms_info = models.BooleanField(default=False)
    has_bedrooms_info  = models.BooleanField(default=False)

    # ── AI fields (populated later by your models) ──
    predicted_price = models.FloatField(null=True, blank=True)

    # ── timestamps ──
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['governorate']),
            models.Index(fields=['city']),
            models.Index(fields=['property_type']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.title} — {self.city}"