import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  Search,
  Sparkles,
  Brain,
  MessageSquareText,
  LineChart,
  LayoutGrid,
  Database,
  ShieldCheck,
  Zap,
  MapPin,
  ArrowRight,
  Star,
  Cpu,
  Workflow,
} from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { getCoords } from "@/lib/tunisia-geocoding";
import type { ListingCard, PaginatedListings } from "@/types/listing";
import heroBg from "@/assets/hero-bg.jpg";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

const TunisiaMap = lazy(() => import("@/components/TunisiaMap"));

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "LensEstate — AI real estate intelligence" },
      {
        name: "description",
        content:
          "AI-powered property valuation, forecasting and discovery. Make smarter real-estate decisions with transparent, data-driven insights.",
      },
      { property: "og:title", content: "LensEstate — AI real estate intelligence" },
      { property: "og:description", content: "AI-powered valuation, forecasting and discovery." },
    ],
  }),
  component: LandingPage,
});

// initial: false avoids SSR + first paint with opacity:0 (looks like a blank page if
// hydration is delayed or whileInView has not run yet).
const fadeUp = {
  initial: false,
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.6, ease: [0.21, 1.02, 0.73, 0.99] as const },
};

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        className="absolute inset-0 -z-10 opacity-40"
        style={{
          backgroundImage: `url(${heroBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          maskImage: "radial-gradient(ellipse at center, black 40%, transparent 80%)",
        }}
      />
      <div className="absolute inset-0 -z-10" style={{ background: "var(--gradient-hero)" }} />
      <div className="mx-auto max-w-7xl px-6 pt-24 pb-32 text-center">
        <motion.div {...fadeUp}>
          <span className="inline-flex items-center gap-2 rounded-full border border-border glass px-4 py-1.5 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 gold-text" />
            Powered by next-gen AI models
          </span>
        </motion.div>
        <motion.h1
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.05 }}
          className="mt-6 text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05]"
        >
          AI-powered real estate
          <br />
          <span className="text-gradient">intelligence</span>
        </motion.h1>
        <motion.p
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.1 }}
          className="mt-6 max-w-2xl mx-auto text-base sm:text-lg text-muted-foreground"
        >
          Aggregate listings from across the market, get transparent valuations, and forecast
          tomorrow's prices — all from one premium AI platform.
        </motion.p>

        <motion.div
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.15 }}
          className="mt-10 mx-auto max-w-3xl"
        >
          <div className="glass rounded-2xl p-2 flex flex-col md:flex-row items-stretch gap-2 shadow-2xl">
            <div className="flex items-center gap-2 px-4 flex-1">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Tunis, Sousse, Sfax…"
                className="bg-transparent outline-none w-full py-3 text-sm placeholder:text-muted-foreground"
              />
            </div>
            <div className="hidden md:block w-px bg-border my-2" />
            <select className="bg-transparent outline-none px-4 py-3 text-sm text-muted-foreground">
              <option className="bg-background">Any type</option>
              <option className="bg-background">Apartment</option>
              <option className="bg-background">Villa</option>
              <option className="bg-background">Land</option>
            </select>
            <div className="hidden md:block w-px bg-border my-2" />
            <select className="bg-transparent outline-none px-4 py-3 text-sm text-muted-foreground">
              <option className="bg-background">Any price</option>
              <option className="bg-background">€100k – €250k</option>
              <option className="bg-background">€250k – €500k</option>
              <option className="bg-background">€500k+</option>
            </select>
            <button className="rounded-xl bg-[var(--gradient-primary)] px-5 py-3 text-sm font-medium text-white inline-flex items-center justify-center gap-2 hover:scale-[1.02] transition-transform glow-purple">
              <Search className="h-4 w-4" /> Search
            </button>
          </div>
        </motion.div>

        <motion.div
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.2 }}
          className="mt-8 flex flex-wrap justify-center gap-3"
        >
          <Link
            to="/map"
            className="rounded-xl bg-[var(--gradient-primary)] px-6 py-3 text-sm font-medium text-white inline-flex items-center gap-2 glow-purple hover:scale-105 transition"
          >
            Explore Properties <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            to="/ai-chat"
            className="rounded-xl border border-border glass px-6 py-3 text-sm font-medium inline-flex items-center gap-2 hover:border-secondary transition"
          >
            <Brain className="h-4 w-4 gold-text" /> Try AI
          </Link>
        </motion.div>

        <div className="mt-16 grid grid-cols-2 gap-6 max-w-md mx-auto">
          {[
            { v: "120K+", l: "Listings" },
            { v: "24/7", l: "AI Insights" },
          ].map((s) => (
            <div key={s.l} className="text-center">
              <div className="text-2xl md:text-3xl font-bold text-gradient">{s.v}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ValueSection() {
  const items = [
    {
      icon: Database,
      title: "Data aggregation",
      desc: "Unified listings from agencies, portals and public records — one source of truth.",
    },
    {
      icon: ShieldCheck,
      title: "Transparent pricing",
      desc: "Every valuation is explainable. See the data behind every number.",
    },
    {
      icon: Cpu,
      title: "AI-driven insights",
      desc: "State-of-the-art models tailored to local markets and architecture.",
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">A new lens on real estate</h2>
        <p className="mt-4 text-muted-foreground">
          Built on three pillars that make property decisions clear and fast.
        </p>
      </motion.div>
      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {items.map((it, i) => (
          <motion.div
            key={it.title}
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: i * 0.08 }}
            className="group relative rounded-2xl glass p-7 hover:border-secondary/60 transition-all hover:-translate-y-1"
          >
            <div
              className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition pointer-events-none"
              style={{ background: "var(--gradient-hero)" }}
            />
            <div className="relative">
              <div className="h-12 w-12 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center glow-purple">
                <it.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="mt-5 text-lg font-semibold">{it.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{it.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function AIFeatures() {
  const features = [
    {
      icon: LineChart,
      title: "Price Prediction",
      desc: "Estimate any property's value with confidence scores and explanations.",
      to: "/price-prediction" as const,
    },
    {
      icon: MessageSquareText,
      title: "AI Chat Assistant",
      desc: "Ask anything about the market, properties, or investment strategy.",
      to: "/ai-chat" as const,
    },
    {
      icon: LayoutGrid,
      title: "2D Plan Generator",
      desc: "Generate floor plans from a few inputs in seconds.",
      to: "/plan-generator" as const,
    },
    {
      icon: Zap,
      title: "Market Forecasting",
      desc: "See where prices are heading by region with predictive models.",
      to: "/forecasting" as const,
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <motion.div {...fadeUp} className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <span className="text-xs uppercase tracking-widest gold-text font-semibold">
            AI Suite
          </span>
          <h2 className="mt-2 text-3xl md:text-5xl font-bold tracking-tight">
            Four AI tools, one platform
          </h2>
        </div>
        <p className="text-muted-foreground max-w-md">
          Tap any module — they share the same intelligence layer.
        </p>
      </motion.div>
      <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: i * 0.06 }}
          >
            <Link
              to={f.to}
              className="group relative block rounded-2xl glass p-6 h-full overflow-hidden transition-all hover:-translate-y-1 hover:border-secondary/70"
            >
              <div
                className="absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition"
                style={{ boxShadow: "0 0 60px oklch(0.48 0.22 290 / 0.5)" }}
              />
              <div className="relative">
                <div className="h-11 w-11 rounded-xl bg-surface flex items-center justify-center border border-border group-hover:bg-[var(--gradient-primary)] transition-colors">
                  <f.icon className="h-5 w-5 group-hover:text-white" />
                </div>
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
                <div className="mt-4 inline-flex items-center text-xs gold-text">
                  Try it <ArrowRight className="ml-1 h-3 w-3" />
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function MapPreview() {
  const [previewProperties, setPreviewProperties] = useState<
    Array<{
      id: string;
      title: string;
      price: number | null;
      region: string;
      image: string;
      lat: number;
      lng: number;
    }>
  >([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const loadPreviewListings = async () => {
      try {
        const response = await apiRequest<PaginatedListings>("/api/listings/?ordering=-created_at");
        const mapped = response.results
          .map((listing: ListingCard) => {
            const coords = getCoords(listing.governorate, listing.city);
            if (!coords) return null;
            return {
              id: String(listing.id),
              title: listing.title,
              price: listing.price,
              region: listing.city || listing.governorate,
              image: listing.image_urls?.[0] || "https://placehold.co/400x280?text=LensEstate",
              lat: coords[0],
              lng: coords[1],
            };
          })
          .filter((item): item is NonNullable<typeof item> => item !== null)
          .slice(0, 8);

        setPreviewProperties(mapped);
        if (mapped[0]) {
          setSelected(mapped[0].id);
        }
      } catch {
        setPreviewProperties([]);
      }
    };

    loadPreviewListings();
  }, []);

  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <div className="grid lg:grid-cols-2 gap-12 items-center">
        <motion.div {...fadeUp}>
          <span className="text-xs uppercase tracking-widest gold-text font-semibold">
            Map intelligence
          </span>
          <h2 className="mt-2 text-3xl md:text-5xl font-bold tracking-tight">
            Explore Tunisia in real time
          </h2>
          <p className="mt-4 text-muted-foreground">
            Heat-mapped regions, live price clusters and AI-recommended areas for your budget. Pin a
            city, drop your filters and let the platform surface what matters.
          </p>
          <Link
            to="/map"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[var(--gradient-primary)] px-5 py-3 text-sm text-white glow-purple hover:scale-105 transition"
          >
            Explore Map <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
        <motion.div
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.1 }}
          className="relative"
        >
          <div className="rounded-2xl overflow-hidden glass p-2 shadow-2xl">
            <div className="relative h-[420px] w-full rounded-xl overflow-hidden">
              {mounted && previewProperties.length > 0 ? (
                <Suspense fallback={<div className="h-full w-full bg-surface/40 animate-pulse" />}>
                  <TunisiaMap
                    properties={previewProperties}
                    selected={selected}
                    onSelect={setSelected}
                  />
                </Suspense>
              ) : (
                <div className="h-full w-full bg-surface/40 animate-pulse" />
              )}
            </div>
          </div>
          <div className="absolute -top-4 -right-4 glass rounded-xl px-4 py-2 text-xs animate-pulse-glow z-[600]">
            <span className="gold-text font-semibold">+12.4%</span> Tunis YoY
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      icon: Database,
      title: "Data collection",
      desc: "We aggregate listings, transactions and signals from across the market.",
    },
    {
      icon: Brain,
      title: "AI processing",
      desc: "Models normalize, score and predict prices with explainable outputs.",
    },
    {
      icon: Workflow,
      title: "Insights delivery",
      desc: "Dashboards, chat and APIs deliver insights wherever you work.",
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">How it works</h2>
        <p className="mt-4 text-muted-foreground">
          A streamlined pipeline from raw data to confident decisions.
        </p>
      </motion.div>
      <div className="mt-14 grid gap-6 md:grid-cols-3 relative">
        {steps.map((s, i) => (
          <motion.div
            key={s.title}
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: i * 0.1 }}
            className="rounded-2xl glass p-7 relative"
          >
            <div className="text-xs gold-text font-mono">STEP {String(i + 1).padStart(2, "0")}</div>
            <s.icon className="mt-4 h-8 w-8 text-secondary" />
            <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function Testimonials() {
  const t = [
    {
      name: "Amira B.",
      role: "Investor",
      quote: "LensEstate's forecasts helped me time a portfolio rotation perfectly. Game changer.",
    },
    {
      name: "Karim D.",
      role: "Agent",
      quote: "Clients trust the valuations because every number is explained. We close faster.",
    },
    {
      name: "Sonia M.",
      role: "Buyer",
      quote: "I found a villa 8% below market thanks to the AI insights. Effortless experience.",
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Trusted by professionals</h2>
        <p className="mt-4 text-muted-foreground">
          Agents, investors and homebuyers using LensEstate every day.
        </p>
      </motion.div>
      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {t.map((it, i) => (
          <motion.div
            key={it.name}
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: i * 0.08 }}
            className="rounded-2xl glass p-6"
          >
            <div className="flex gold-text gap-0.5">
              {Array.from({ length: 5 }).map((_, k) => (
                <Star key={k} className="h-4 w-4 fill-current" />
              ))}
            </div>
            <p className="mt-4 text-sm text-foreground/90">"{it.quote}"</p>
            <div className="mt-5 flex items-center gap-3">
              <div className="h-9 w-9 rounded-full bg-[var(--gradient-primary)] flex items-center justify-center text-sm font-semibold">
                {it.name[0]}
              </div>
              <div>
                <div className="text-sm font-medium">{it.name}</div>
                <div className="text-xs text-muted-foreground">{it.role}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <motion.div
        {...fadeUp}
        className="relative overflow-hidden rounded-3xl p-12 md:p-16 text-center"
        style={{ background: "var(--gradient-primary)" }}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{ background: "var(--gradient-hero)" }}
        />
        <div className="relative">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white">
            Start seeing real estate <span className="gold-text">clearly</span>
          </h2>
          <p className="mt-4 text-white/80 max-w-xl mx-auto">
            Create your free account and unlock AI valuations, forecasting and personalized
            recommendations.
          </p>
          <Link
            to="/auth"
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-primary hover:scale-105 transition glow-gold"
          >
            Sign up free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </motion.div>
    </section>
  );
}

function LandingPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main>
        <Hero />
        <ValueSection />
        <AIFeatures />
        <MapPreview />
        <HowItWorks />
        <Testimonials />
        <FinalCTA />
      </main>
      <SiteFooter />
    </div>
  );
}
