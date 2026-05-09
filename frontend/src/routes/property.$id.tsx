import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Heart, MapPin, Bed, Bath, Square, Sparkles, TrendingUp, ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { SiteHeader } from "@/components/SiteHeader";
import type { Favorite } from "@/types/user";
import type { ListingDetail } from "@/types/listing";

export const Route = createFileRoute("/property/$id")({
  head: () => ({
    meta: [
      { title: "Property details — LensEstate" },
      { name: "description", content: "Detailed property view with AI valuation and insights." },
    ],
  }),
  component: PropertyPage,
});

function PropertyPage() {
  const { id } = Route.useParams();
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(0);
  const [fav, setFav] = useState(false);
  const [favoriteId, setFavoriteId] = useState<number | null>(null);
  const images = useMemo(() => {
    if (!listing) return ["https://placehold.co/1200x700?text=LensEstate"];
    return listing.image_urls.length > 0
      ? listing.image_urls
      : ["https://placehold.co/1200x700?text=LensEstate"];
  }, [listing]);

  useEffect(() => {
    const loadListing = async () => {
      setLoading(true);
      try {
        const response = await apiRequest<ListingDetail>(`/api/listings/${id}/`, {
          skipAuth: true,
        });
        setListing(response);
      } finally {
        setLoading(false);
      }
    };

    loadListing();
  }, [id]);

  useEffect(() => {
    const loadFavoriteStatus = async () => {
      if (isAuthLoading || !isAuthenticated || !listing) return;
      try {
        const favorites = await apiRequest<Favorite[]>("/api/users/favorites/");
        const existing = favorites.find((item) => item.listing_id === listing.id);
        setFav(Boolean(existing));
        setFavoriteId(existing?.id ?? null);
      } catch (err) {
        console.error("Failed to load favorites", err);
        setFav(false);
        setFavoriteId(null);
      }
    };
    loadFavoriteStatus();
  }, [isAuthenticated, isAuthLoading, listing]);

  const toggleFavorite = async () => {
    if (!isAuthenticated || !listing) return;
    if (fav && favoriteId) {
      await apiRequest<void>(`/api/users/favorites/${favoriteId}/`, { method: "DELETE" });
      setFav(false);
      setFavoriteId(null);
      return;
    }

    await apiRequest<Favorite>("/api/users/favorites/", {
      method: "POST",
      body: JSON.stringify({ listing_id: listing.id }),
    });

    const favorites = await apiRequest<Favorite[]>("/api/users/favorites/");
    const existing = favorites.find((item) => item.listing_id === listing.id);
    setFav(Boolean(existing));
    setFavoriteId(existing?.id ?? null);
  };

  const insights = listing?.ai_insights;

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-6 py-10">
        <Link
          to="/map"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="h-4 w-4" /> Back to map
        </Link>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {loading && (
              <div className="text-sm text-muted-foreground mb-3">Loading property details...</div>
            )}
            <motion.img
              key={active}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              src={images[active]}
              alt={listing?.title || "Property"}
              className="w-full h-[440px] object-cover rounded-2xl shadow-2xl"
            />
            <div className="mt-3 grid grid-cols-3 gap-3">
              {images.map((img, i) => (
                <button
                  key={i}
                  onClick={() => setActive(i)}
                  className={`rounded-xl overflow-hidden border-2 transition ${active === i ? "border-accent" : "border-transparent"}`}
                >
                  <img src={img} alt="thumb" className="h-24 w-full object-cover" loading="lazy" />
                </button>
              ))}
            </div>

            <div className="mt-8">
              <h1 className="text-3xl font-bold">{listing?.title || `Property #${id}`}</h1>
              <div className="mt-2 text-muted-foreground flex items-center gap-2">
                <MapPin className="h-4 w-4" /> {listing?.city || listing?.governorate || "Tunisia"},
                Tunisia
              </div>

              <div className="mt-6 grid grid-cols-3 gap-4">
                <Stat icon={Bed} label="Bedrooms" value={`${listing?.bedrooms ?? 0}`} />
                <Stat icon={Bath} label="Bathrooms" value={`${listing?.bathrooms ?? 0}`} />
                <Stat icon={Square} label="Surface" value={`${listing?.surface_m2 ?? 0} m²`} />
              </div>

              <div className="mt-8">
                <h2 className="text-xl font-semibold">About this property</h2>
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                  {listing?.description || "No description available."}
                </p>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            <div className="rounded-2xl glass p-6">
              <div className="text-xs text-muted-foreground">Listed price</div>
              <div className="mt-1 text-4xl font-bold gold-text">
                {listing?.price ? `${listing.price.toLocaleString()} TND` : "Price on request"}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {listing?.price && listing.surface_m2
                  ? `${Math.round(listing.price / listing.surface_m2).toLocaleString()} TND / m²`
                  : "-"}
              </div>

              <button
                onClick={toggleFavorite}
                className={`mt-5 w-full rounded-xl border py-2.5 text-sm font-medium inline-flex items-center justify-center gap-2 transition ${fav ? "border-accent bg-accent/10 text-accent" : "border-border hover:border-secondary"}`}
              >
                <Heart className={`h-4 w-4 ${fav ? "fill-current" : ""}`} />{" "}
                {fav ? "Saved" : "Add to favorites"}
              </button>
              <button className="mt-2 w-full rounded-xl bg-[var(--gradient-primary)] py-2.5 text-sm font-medium text-white glow-purple">
                Contact agent
              </button>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl p-6 relative overflow-hidden"
              style={{ background: "var(--gradient-primary)" }}
            >
              <div
                className="absolute inset-0 opacity-30"
                style={{ background: "var(--gradient-hero)" }}
              />
              <div className="relative">
                <div className="flex items-center gap-2 text-white/80 text-xs uppercase tracking-widest">
                  <Sparkles className="h-3.5 w-3.5 gold-text" /> AI Insights
                </div>
                <div className="mt-3">
                  <div className="text-xs text-white/70">Estimated fair price</div>
                  <div className="text-3xl font-bold text-white">
                    {insights?.predicted_price
                      ? `${insights.predicted_price.toLocaleString()} TND`
                      : "N/A"}
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-white">
                  <div>
                    <div className="text-xs text-white/70">Confidence</div>
                    <div className="text-lg font-semibold gold-text">
                      {insights?.confidence ? `${insights.confidence}%` : "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-white/70">Trend</div>
                    <div className="text-lg font-semibold flex items-center gap-1">
                      {insights?.trend && insights.trend > 0 ? (
                        <>
                          <TrendingUp className="h-4 w-4" />
                          {`+${insights.trend}%`}
                        </>
                      ) : insights?.trend && insights.trend < 0 ? (
                        <>
                          <TrendingUp className="h-4 w-4 rotate-180" />
                          {`${insights.trend}%`}
                        </>
                      ) : (
                        "N/A"
                      )}
                    </div>
                  </div>
                </div>
                <p className="mt-4 text-xs text-white/80 leading-relaxed">
                  AI insight values are shown when prediction data is available for this listing.
                </p>
              </div>
            </motion.div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Bed; label: string; value: string }) {
  return (
    <div className="rounded-xl glass p-4">
      <Icon className="h-4 w-4 gold-text" />
      <div className="text-xs text-muted-foreground mt-2">{label}</div>
      <div className="text-base font-semibold mt-0.5">{value}</div>
    </div>
  );
}
