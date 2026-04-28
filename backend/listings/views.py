from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from .models import Listing
from .serializers import ListingCardSerializer, ListingDetailSerializer


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly — listings come from pgAdmin import, not user submissions.
    Supports filtering via URL params:
    /api/listings/?governorate=Tunis&transaction_type=sale&min_price=50000
    """
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'city', 'governorate']
    ordering_fields = ['price', 'surface_m2', 'created_at']

    def get_queryset(self):
        qs = Listing.objects.all()
        p = self.request.query_params

        # filters
        if p.get('governorate'):
            qs = qs.filter(governorate__iexact=p['governorate'])
        if p.get('city'):
            qs = qs.filter(city__iexact=p['city'])
        if p.get('property_type'):
            qs = qs.filter(property_type__iexact=p['property_type'])
        if p.get('transaction_type'):
            qs = qs.filter(transaction_type__iexact=p['transaction_type'])
        if p.get('min_price'):
            qs = qs.filter(price__gte=float(p['min_price']))
        if p.get('max_price'):
            qs = qs.filter(price__lte=float(p['max_price']))
        if p.get('min_surface'):
            qs = qs.filter(surface_m2__gte=float(p['min_surface']))
        if p.get('rooms'):
            qs = qs.filter(rooms=float(p['rooms']))
        if p.get('has_pool') == 'true':
            qs = qs.filter(has_pool=True)
        if p.get('has_parking') == 'true':
            qs = qs.filter(has_parking=True)
        if p.get('has_garden') == 'true':
            qs = qs.filter(has_garden=True)

        return qs

    def get_serializer_class(self):
        # list view → light, detail view → full
        if self.action == 'retrieve':
            return ListingDetailSerializer
        return ListingCardSerializer