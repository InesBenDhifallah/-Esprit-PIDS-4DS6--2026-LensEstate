import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { TrendingUp, MapPin, Activity } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { get } from "@/lib/api";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from "recharts";

export const Route = createFileRoute("/forecasting")({
  head: () => ({
    meta: [
      { title: "Market Forecasting — LensEstate" },
      { name: "description", content: "Predictive market trends by region across Tunisia." },
    ],
  }),
  component: ForecastPage,
});

type ForecastPoint = {
  m: string;
  price: number | null;
  forecast: number | null;
  lower?: number | null;
  upper?: number | null;
};

type ForecastRegionGrowth = {
  name: string;
  growth: number;
};

type ForecastModel = {
  name: string;
  mape: number;
  reliability: string;
};

type ForecastResponse = {
  region: string;
  current_avg: number;
  forecast_12m: number;
  confidence: number;
  projected_growth_pct: number;
  series: ForecastPoint[];
  regions: ForecastRegionGrowth[];
  model?: ForecastModel;
};

// Fallback data structure for loading state
const skeletonSeries = Array.from({ length: 12 }).map((_, i) => ({
  m: `M${i}`, price: 1000 + Math.random() * 200, forecast: null, lower: null, upper: null
}));

const availableRegions = [
  "Tunis", "Ariana", "Ben Arous", "Nabeul", "Sousse", "Monastir", "Mahdia", "Sfax", "Bizerte", "Medenine"
];

function formatTND(value: number): string {
  return new Intl.NumberFormat('fr-FR').format(value).replace(/\s/g, ' ') + ' DT';
}

function ForecastPage() {
  const [region, setRegion] = useState("Tunis");
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);

    async function loadForecast() {
      try {
        const res = await get<ForecastResponse>(
          `/api/forecasting/?region=${encodeURIComponent(region)}`,
          { skipAuth: true },
        );
        if (cancelled) return;
        setData(res);
      } catch {
        // Handle error gracefully
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadForecast();
    return () => {
      cancelled = true;
    };
  }, [region]);

  const growthText = useMemo(() => {
    if (!data) return "Calcul en cours...";
    const sign = data.projected_growth_pct >= 0 ? "+" : "";
    return `${sign}${data.projected_growth_pct}% projected`;
  }, [data]);

  return (
    <div className="min-h-screen pb-20">
      <SiteHeader />

      <main className="mx-auto max-w-[1400px] px-6 pt-12">
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row items-start lg:items-end justify-between gap-8 mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 gold-text" />
              <span className="text-xs uppercase tracking-widest gold-text font-semibold">LensEstate Intelligence</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight">Market Forecast</h1>
            <p className="mt-3 text-lg text-muted-foreground max-w-2xl">
              Sophisticated AI-driven predictive modeling for real estate trends across Tunisia.
            </p>
          </motion.div>

          {/* Premium Region Selector */}
          <motion.div
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
            className="flex flex-wrap gap-2 p-1.5 rounded-2xl glass border border-white/5 bg-black/20 backdrop-blur-xl"
          >
            {availableRegions.slice(0, 6).map((r) => (
              <button
                key={r}
                onClick={() => setRegion(r)}
                className={`relative px-5 py-2.5 rounded-xl text-sm font-medium transition-colors duration-300 ${region === r ? "text-black" : "text-zinc-400 hover:text-white"
                  }`}
              >
                {region === r && (
                  <motion.div
                    layoutId="active-region-pill"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-yellow-500/90 to-yellow-200/90 shadow-[0_0_20px_rgba(234,179,8,0.3)]"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{r}</span>
              </button>
            ))}
          </motion.div>
        </div>

        {/* KPIs Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <KPI
            label="Current Average"
            value={isLoading || !data ? "---" : `${formatTND(data.current_avg)}/m²`}
            sub="Based on recent listings"
            delay={0.1}
          />
          <KPI
            label="12-Mo Forecast"
            value={isLoading || !data ? "---" : `${formatTND(data.forecast_12m)}/m²`}
            sub={growthText}
            highlight
            delay={0.2}
          />
          <KPI
            label="Model Confidence"
            value={isLoading || !data ? "---" : `${data.confidence}%`}
            sub="Algorithm certainty"
            delay={0.3}
          />
        </div>

        {/* Main Charts Section */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Timeline Chart */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.4 }}
            className="lg:col-span-2 rounded-3xl glass p-6 md:p-8 border border-white/5 relative"
          >
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <MapPin className="h-5 w-5 gold-text" />
                  {region} Trajectory
                </h2>
                <p className="text-sm text-muted-foreground mt-1">Historical data and AI projections</p>
              </div>
              <div className="flex gap-4">
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <div className="w-3 h-3 rounded-full bg-cyan-500/80 shadow-[0_0_10px_rgba(6,182,212,0.5)]" /> Historical
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <div className="w-3 h-3 rounded-full bg-amber-500/80 shadow-[0_0_10px_rgba(245,158,11,0.5)]" /> Forecast
                </div>
              </div>
            </div>

            <div className="h-[400px] w-full">
              {isLoading ? (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="h-8 w-8 rounded-full border-2 border-amber-500/20 border-t-amber-500 animate-spin" />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data?.series || skeletonSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis
                      dataKey="m"
                      stroke="rgba(255,255,255,0.4)"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      dy={10}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.4)"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                    <Area
                      type="monotone"
                      dataKey={["lower", "upper"]}
                      stroke="none"
                      fill="#f59e0b"
                      fillOpacity={0.15}
                      activeDot={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="#06b6d4"
                      strokeWidth={3}
                      fill="url(#colorPrice)"
                      activeDot={{ r: 6, fill: "#06b6d4", stroke: "#fff", strokeWidth: 2 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="forecast"
                      stroke="#f59e0b"
                      strokeWidth={3}
                      strokeDasharray="6 4"
                      fill="url(#colorForecast)"
                      activeDot={{ r: 6, fill: "#f59e0b", stroke: "#fff", strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </motion.div>

          {/* Regional Growth Comparison */}
          <motion.div
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, delay: 0.6 }}
            className="rounded-3xl glass p-6 md:p-8 border border-white/5"
          >
            <h2 className="text-xl font-semibold mb-2">Regional Outlook</h2>
            <p className="text-sm text-muted-foreground mb-8">Projected 12-month growth</p>

            <div className="h-[350px]">
              {isLoading ? (
                <div className="w-full h-full flex flex-col justify-between py-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-full h-8 bg-white/5 animate-pulse rounded-lg" />
                  ))}
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data?.regions || []} layout="vertical" margin={{ top: 0, right: 0, left: 20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="rgba(255,255,255,0.02)" />
                    <XAxis type="number" hide />
                    <YAxis
                      dataKey="name"
                      type="category"
                      axisLine={false}
                      tickLine={false}
                      stroke="rgba(255,255,255,0.6)"
                      fontSize={12}
                      width={80}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                      contentStyle={{ background: "rgba(10,10,10,0.8)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "12px" }}
                      formatter={(value: number) => [`${value}%`, "Growth"]}
                    />
                    <Bar dataKey="growth" radius={[0, 6, 6, 0]} barSize={24}>
                      {data?.regions.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.name === region ? "#f59e0b" : "rgba(255,255,255,0.15)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/5 text-sm text-zinc-400 leading-relaxed">
              <TrendingUp className="h-4 w-4 mb-2 gold-text" />
              This outlook compares the expected appreciation rates across major Tunisian governorates based on AI modeling.
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

// Custom Premium Tooltip for Recharts
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass !bg-black/40 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl">
        <p className="text-white/60 text-xs font-semibold mb-2 uppercase tracking-wider">{label}</p>
        {payload.map((entry: any, index: number) => {
          if (Array.isArray(entry.value)) return null;
          return (
            <div key={index} className="flex items-center gap-3 mt-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-white font-medium">
                {entry.name === "price" ? "Historical" : "Forecast"}:
                <span className="ml-2 font-mono">{formatTND(entry.value)}</span>
              </span>
            </div>
          );
        })}
      </div>
    );
  }
  return null;
};

// Animated KPI Card
function KPI({ label, value, sub, highlight, delay = 0 }: { label: string; value: string; sub: string; highlight?: boolean; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`rounded-3xl p-6 relative overflow-hidden group transition-all duration-500 hover:-translate-y-1 ${highlight ? "shadow-[0_10px_40px_rgba(212,175,55,0.15)]" : "glass border border-white/5"
        }`}
      style={highlight ? { background: "linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(0,0,0,0) 100%), var(--glass-bg)" } : {}}
    >
      {highlight && (
        <div className="absolute top-0 right-0 p-4 opacity-30">
          <TrendingUp className="h-12 w-12 text-yellow-500" />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <div className={`text-xs uppercase tracking-widest relative z-10 ${highlight ? "gold-text" : "text-muted-foreground"}`}>{label}</div>
      <div className="mt-3 text-3xl font-bold tracking-tight text-white/95 relative z-10">{value}</div>
      <div className={`mt-2 text-xs flex items-center gap-1.5 font-medium relative z-10 ${highlight ? "text-yellow-500/80" : "text-zinc-500"}`}>
        {sub}
      </div>
    </motion.div>
  );
}
