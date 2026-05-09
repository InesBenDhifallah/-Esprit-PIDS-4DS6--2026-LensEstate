export interface ListingCard {
  id: number;
  listing_id: string;
  title: string;
  property_type: string;
  transaction_type: string;
  price: number | null;
  currency: string;
  surface_m2: number | null;
  rooms: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  governorate: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
  image_urls: string[];
  has_images: boolean;
  is_agency: boolean;
}

export interface ListingDetail extends ListingCard {
  description: string;
  has_elevator: boolean;
  has_parking: boolean;
  has_pool: boolean;
  has_garden: boolean;
  has_furniture: boolean;
  has_air_conditioning: boolean;
  has_heating: boolean;
  has_terrace: boolean;
  has_sea_view: boolean;
  has_security: boolean;
  has_basement: boolean;
  has_standing: boolean;
  seller_type: string;
  listing_url: string;
  source: string;
  predicted_price: number | null;
  ai_insights?: {
    predicted_price: number | null;
    confidence: number;
    trend: number;
  };
  created_at: string;
}

export interface PaginatedListings {
  count: number;
  next: string | null;
  previous: string | null;
  results: ListingCard[];
}
