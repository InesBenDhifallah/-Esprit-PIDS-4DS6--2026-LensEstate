import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  MapPin,
  Bed,
  Bath,
  Square,
  ArrowRight,
  SlidersHorizontal,
  Map as MapIcon,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { apiRequest, buildListingsQuery, type ApiPaginatedResponse } from "@/lib/api";
import type { ListingCard } from "@/types/listing";

export const Route = createFileRoute("/listings")({
  head: () => ({
    meta: [
      { title: "Listings — LensEstate" },
      {
        name: "description",
        content:
          "Browse all available properties across Tunisia, one listing per row with full details.",
      },
      { property: "og:title", content: "Listings — LensEstate" },
      { property: "og:description", content: "Browse all available properties across Tunisia." },
    ],
  }),
  component: ListingsPage,
});

function ListingsPage() {
  const [listings, setListings] = useState<ListingCard[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [transactionType, setTransactionType] = useState("");
  const [ordering, setOrdering] = useState("-created_at");

  const totalPages = useMemo(() => Math.max(1, Math.ceil(count / 20)), [count]);

  useEffect(() => {
    const loadListings = async () => {
      setLoading(true);
      try {
        const query = buildListingsQuery({
          page,
          search,
          city,
          property_type: propertyType,
          transaction_type: transactionType,
          ordering,
        });
        const response = await apiRequest<ApiPaginatedResponse<ListingCard>>(
          `/api/listings/${query}`,
        );
        setListings(response.results);
        setCount(response.count);
      } catch {
        setListings([]);
        setCount(0);
      } finally {
        setLoading(false);
      }
    };

    loadListings();
  }, [page, search, city, propertyType, transactionType, ordering]);

  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-6xl w-full px-6 py-10">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
          <div>
            <span className="text-xs uppercase tracking-widest gold-text font-semibold">
              Search results
            </span>
            <h1 className="mt-2 text-3xl md:text-4xl font-bold tracking-tight">
              {count} properties matched
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Filtered listings across Tunisia, sorted by AI relevance.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/map"
              className="inline-flex items-center gap-2 rounded-xl border border-border glass px-4 py-2.5 text-sm hover:border-secondary transition"
            >
              <MapIcon className="h-4 w-4 gold-text" /> View on map
            </Link>
            <Link
              to="/map"
              className="inline-flex items-center gap-2 rounded-xl bg-[var(--gradient-primary)] px-4 py-2.5 text-sm text-white glow-purple hover:scale-105 transition"
            >
              <SlidersHorizontal className="h-4 w-4" /> Edit filters
            </Link>
          </div>
        </div>

        <div className="mb-6 grid gap-3 md:grid-cols-5">
          <input
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            placeholder="Search keywords"
            className="rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
          />
          <input
            value={city}
            onChange={(e) => {
              setPage(1);
              setCity(e.target.value);
            }}
            placeholder="City"
            className="rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
          />
          <input
            value={propertyType}
            onChange={(e) => {
              setPage(1);
              setPropertyType(e.target.value);
            }}
            placeholder="Property type"
            className="rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
          />
          <select
            value={transactionType}
            onChange={(e) => {
              setPage(1);
              setTransactionType(e.target.value);
            }}
            className="rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
          >
            <option value="">All transactions</option>
            <option value="sale">Sale</option>
            <option value="rent">Rent</option>
          </select>
          <select
            value={ordering}
            onChange={(e) => {
              setPage(1);
              setOrdering(e.target.value);
            }}
            className="rounded-xl border border-border bg-surface/40 px-3 py-2 text-sm outline-none"
          >
            <option value="-created_at">Newest</option>
            <option value="price">Price ascending</option>
            <option value="-price">Price descending</option>
            <option value="surface_m2">Surface ascending</option>
            <option value="-surface_m2">Surface descending</option>
          </select>
        </div>

        <div className="space-y-5">
          {loading && <div className="text-sm text-muted-foreground">Loading listings...</div>}
          {!loading &&
            listings.map((l, i) => (
              <motion.div
                key={l.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.06 }}
              >
                <Link
                  to="/property/$id"
                  params={{ id: String(l.id) }}
                  className="group block rounded-2xl glass overflow-hidden hover:border-secondary/70 transition-all hover:-translate-y-0.5"
                >
                  <div className="grid md:grid-cols-[280px_1fr_220px] gap-0">
                    <div className="relative h-56 md:h-auto overflow-hidden">
                      <img
                        src={l.image_urls?.[0] || "https://placehold.co/400x280?text=LensEstate"}
                        alt={l.title}
                        loading="lazy"
                        className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                      <div className="absolute top-3 left-3 rounded-full bg-black/60 backdrop-blur px-3 py-1 text-xs text-white">
                        {l.property_type}
                      </div>
                    </div>

                    <div className="p-6 flex flex-col justify-center">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 gold-text" /> {l.city || l.governorate},
                        Tunisia
                      </div>
                      <h2 className="mt-1.5 text-xl font-semibold group-hover:text-gradient transition-all">
                        {l.title}
                      </h2>
                      <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                        {l.transaction_type} {l.property_type} in {l.city || l.governorate}.
                      </p>
                      <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
                        <span className="inline-flex items-center gap-1.5">
                          <Bed className="h-4 w-4 text-secondary" /> {l.bedrooms ?? 0} beds
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <Bath className="h-4 w-4 text-secondary" /> {l.bathrooms ?? 0} baths
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <Square className="h-4 w-4 text-secondary" /> {l.surface_m2 ?? 0} m²
                        </span>
                      </div>
                    </div>

                    <div className="p-6 border-t md:border-t-0 md:border-l border-border flex flex-col justify-center items-start md:items-end gap-3 bg-surface/30">
                      <div>
                        <div className="text-xs text-muted-foreground md:text-right">
                          Asking price
                        </div>
                        <div className="text-2xl font-bold gold-text">
                          {l.price ? `${l.price.toLocaleString()} TND` : "Price on request"}
                        </div>
                        <div className="text-xs text-muted-foreground md:text-right mt-0.5">
                          {l.price && l.surface_m2
                            ? `${Math.round(l.price / l.surface_m2).toLocaleString()} TND / m²`
                            : "-"}
                        </div>
                      </div>
                      <div className="inline-flex items-center gap-1.5 text-xs rounded-full border border-secondary/40 bg-secondary/10 px-2.5 py-1">
                        <Sparkles className="h-3 w-3 gold-text" /> AI verified
                      </div>
                      <span className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium text-foreground group-hover:gold-text transition">
                        View details <ArrowRight className="h-4 w-4" />
                      </span>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          {!loading && listings.length === 0 && (
            <div className="text-sm text-muted-foreground">
              No listings found for current filters.
            </div>
          )}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
            className="rounded-xl border border-border px-4 py-2 text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <div className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </div>
          <button
            type="button"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page >= totalPages}
            className="rounded-xl border border-border px-4 py-2 text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
