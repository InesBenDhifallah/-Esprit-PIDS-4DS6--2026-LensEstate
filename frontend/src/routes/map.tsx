import { createFileRoute, Link } from "@tanstack/react-router";
import { Filter, MapPin, Bed, Bath, Square, SlidersHorizontal } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { apiRequest, buildListingsQuery, type ApiPaginatedResponse } from "@/lib/api";
import { getCoords } from "@/lib/tunisia-geocoding";
import { SiteHeader } from "@/components/SiteHeader";
import type { ListingCard } from "@/types/listing";

const TunisiaMap = lazy(() => import("@/components/TunisiaMap"));

export const Route = createFileRoute("/map")({
  head: () => ({
    meta: [
      { title: "Explore the map — LensEstate" },
      {
        name: "description",
        content: "Browse properties across Tunisia on an interactive AI-enhanced map.",
      },
    ],
  }),
  component: MapPage,
});

type Property = {
  id: string;
  title: string;
  price: number | null;
  region: string;
  beds: number;
  baths: number;
  size: number;
  image: string;
  lat: number;
  lng: number;
};

function MapPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [city, setCity] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [rooms, setRooms] = useState("");
  const [transactionType, setTransactionType] = useState("");

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    let isCancelled = false;

    const loadMapListings = async () => {
      const baseParams = {
        city,
        property_type: propertyType,
        rooms,
        transaction_type: transactionType,
      };

      // Important: avoid fetching every paginated page (can trigger 429 throttling).
      // Fetch a single, larger page for map markers.
      const query = buildListingsQuery({
        ...baseParams,
        page: 1,
        page_size: 200,
      });
      const response = await apiRequest<ApiPaginatedResponse<ListingCard>>(`/api/listings/${query}`, {
        skipAuth: true,
      });

      const mapped = response.results
        .map((listing) => {
          const coords =
            listing.latitude !== null && listing.longitude !== null
              ? [listing.latitude, listing.longitude] as const
              : getCoords(listing.governorate, listing.city);
          if (!coords) return null;
          return {
            id: String(listing.id),
            title: listing.title,
            price: listing.price,
            region: listing.city || listing.governorate,
            beds: listing.bedrooms ?? 0,
            baths: listing.bathrooms ?? 0,
            size: listing.surface_m2 ?? 0,
            image: listing.image_urls?.[0] || "https://placehold.co/240x140?text=LensEstate",
            lat: coords[0],
            lng: coords[1],
          };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null);

      if (isCancelled) return;

      setProperties(mapped);
      if (mapped[0]) {
        setSelected((current) =>
          current && mapped.some((property) => property.id === current) ? current : mapped[0].id,
        );
      } else {
        setSelected(null);
      }
    };

    loadMapListings().catch(() => {
      if (isCancelled) return;
      setProperties([]);
      setSelected(null);
    });

    return () => {
      isCancelled = true;
    };
  }, [city, propertyType, rooms, transactionType]);

  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <div className="flex-1 grid lg:grid-cols-[360px_1fr] min-h-[calc(100vh-4rem)]">
        {/* Filters */}
        <aside className="border-r border-border p-6 overflow-y-auto bg-surface/40">
          <div className="flex items-center gap-2 mb-5">
            <SlidersHorizontal className="h-4 w-4 gold-text" />
            <h2 className="font-semibold">Filters</h2>
          </div>
          <FilterGroup title="Price range">
            <input
              type="range"
              min="50000"
              max="1000000"
              defaultValue="500000"
              className="w-full accent-[var(--secondary)]"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>50k TND</span>
              <span>1M TND</span>
            </div>
          </FilterGroup>
          <FilterGroup title="Region">
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="City"
              className="w-full rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
            />
          </FilterGroup>
          <FilterGroup title="Property type">
            <input
              value={propertyType}
              onChange={(e) => setPropertyType(e.target.value)}
              placeholder="Apartment, Villa..."
              className="w-full rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
            />
          </FilterGroup>
          <FilterGroup title="Bedrooms">
            <input
              value={rooms}
              onChange={(e) => setRooms(e.target.value)}
              placeholder="e.g. 3"
              className="w-full rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
            />
          </FilterGroup>
          <FilterGroup title="Transaction">
            <select
              value={transactionType}
              onChange={(e) => setTransactionType(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
            >
              <option value="">All</option>
              <option value="sale">Sale</option>
              <option value="rent">Rent</option>
            </select>
          </FilterGroup>
          <Link
            to="/listings"
            className="w-full mt-4 rounded-xl bg-[var(--gradient-primary)] py-2.5 text-sm font-medium text-white glow-purple inline-flex items-center justify-center"
          >
            <Filter className="h-4 w-4 inline mr-1" /> Apply filters
          </Link>

          <div className="mt-8 space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">
              {properties.length} results
            </h3>
            {properties.map((p) => (
              <Link
                key={p.id}
                to="/property/$id"
                params={{ id: p.id }}
                onMouseEnter={() => setSelected(p.id)}
                className={`block rounded-xl border p-3 transition ${selected === p.id ? "border-secondary bg-secondary/5" : "border-border hover:border-secondary/50"}`}
              >
                <div className="flex gap-3">
                  <img
                    src={p.image}
                    alt={p.title}
                    className="h-16 w-20 rounded-lg object-cover"
                    loading="lazy"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{p.title}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                      <MapPin className="h-3 w-3" />
                      {p.region}
                    </div>
                    <div className="text-sm gold-text font-semibold mt-1">
                      {p.price ? `${p.price.toLocaleString()} TND` : "Price on request"}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </aside>

        {/* Map */}
        <div className="relative bg-surface/20 overflow-hidden">
          {mounted ? (
            <Suspense fallback={<div className="h-full w-full bg-surface/40 animate-pulse" />}>
              <TunisiaMap properties={properties} selected={selected} onSelect={setSelected} />
            </Suspense>
          ) : (
            <div className="h-full w-full bg-surface/40 animate-pulse" />
          )}

          <div className="pointer-events-none absolute top-4 left-1/2 -translate-x-1/2 z-[500] glass rounded-xl px-3 py-2 text-xs text-muted-foreground">
            <MapPin className="inline h-3 w-3 mr-1 gold-text" /> Live AI-enhanced map of Tunisia
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="text-xs uppercase tracking-wider text-muted-foreground mb-2">{title}</h3>
      {children}
    </div>
  );
}

// silence unused
void Bath;
void Square;
