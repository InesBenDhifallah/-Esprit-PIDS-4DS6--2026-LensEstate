import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { TrendingUp, MapPin } from "lucide-react";
import { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
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

const series = [
  { m: "Jan", price: 2100, forecast: 2100 },
  { m: "Feb", price: 2140, forecast: 2150 },
  { m: "Mar", price: 2180, forecast: 2200 },
  { m: "Apr", price: 2220, forecast: 2260 },
  { m: "May", price: 2260, forecast: 2330 },
  { m: "Jun", price: 2300, forecast: 2400 },
  { m: "Jul", price: null, forecast: 2470 },
  { m: "Aug", price: null, forecast: 2540 },
  { m: "Sep", price: null, forecast: 2600 },
];

const regions = [
  { name: "Tunis", growth: 12.4 },
  { name: "Sousse", growth: 8.1 },
  { name: "Sfax", growth: 5.6 },
  { name: "Hammamet", growth: 9.3 },
  { name: "Djerba", growth: 6.2 },
];

function ForecastPage() {
  const [region, setRegion] = useState("Tunis");

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="text-xs uppercase tracking-widest gold-text font-semibold">Market Intelligence</span>
            <h1 className="mt-2 text-4xl md:text-5xl font-bold">Forecasting</h1>
            <p className="mt-2 text-muted-foreground">Where prices are heading, region by region.</p>
          </div>
          <div className="flex gap-2">
            {regions.map((r) => (
              <button key={r.name} onClick={() => setRegion(r.name)} className={`rounded-xl border px-4 py-2 text-sm transition ${region === r.name ? "border-secondary bg-secondary/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}>
                {r.name}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-10 grid lg:grid-cols-3 gap-6">
          <KPI label="Current avg" value="€2,300/m²" sub="Updated daily" />
          <KPI label="12-mo forecast" value="€2,600/m²" sub="+13% projected" highlight />
          <KPI label="Confidence" value="91%" sub="High signal" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="mt-6 rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2"><MapPin className="h-4 w-4 gold-text" />{region} — price trend</h2>
            <span className="text-xs text-muted-foreground">€/m²</span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="oklch(0.48 0.22 290)" stopOpacity={0.7}/>
                    <stop offset="95%" stopColor="oklch(0.48 0.22 290)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="oklch(0.78 0.14 85)" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="oklch(0.78 0.14 85)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.3 0.03 285 / 0.3)" />
                <XAxis dataKey="m" stroke="oklch(0.71 0.015 280)" fontSize={12} />
                <YAxis stroke="oklch(0.71 0.015 280)" fontSize={12} />
                <Tooltip contentStyle={{ background: "oklch(0.21 0.02 280)", border: "1px solid oklch(0.3 0.03 285)", borderRadius: 12 }} />
                <Area type="monotone" dataKey="price" stroke="oklch(0.48 0.22 290)" fill="url(#g1)" strokeWidth={2.5} />
                <Area type="monotone" dataKey="forecast" stroke="oklch(0.78 0.14 85)" fill="url(#g2)" strokeWidth={2.5} strokeDasharray="6 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="mt-6 rounded-2xl glass p-6"
        >
          <h2 className="font-semibold mb-4">Region growth — next 12 months</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={regions}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.3 0.03 285 / 0.3)" />
                <XAxis dataKey="name" stroke="oklch(0.71 0.015 280)" fontSize={12} />
                <YAxis stroke="oklch(0.71 0.015 280)" fontSize={12} unit="%" />
                <Tooltip contentStyle={{ background: "oklch(0.21 0.02 280)", border: "1px solid oklch(0.3 0.03 285)", borderRadius: 12 }} />
                <Bar dataKey="growth" fill="oklch(0.48 0.22 290)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function KPI({ label, value, sub, highlight }: { label: string; value: string; sub: string; highlight?: boolean }) {
  return (
    <div className={`rounded-2xl p-6 ${highlight ? "" : "glass"}`} style={highlight ? { background: "var(--gradient-primary)" } : {}}>
      <div className={`text-xs uppercase tracking-widest ${highlight ? "text-white/80" : "text-muted-foreground"}`}>{label}</div>
      <div className={`mt-2 text-3xl font-bold ${highlight ? "text-white" : ""}`}>{value}</div>
      <div className={`mt-1 text-xs flex items-center gap-1 ${highlight ? "gold-text" : "text-muted-foreground"}`}>
        <TrendingUp className="h-3 w-3" /> {sub}
      </div>
    </div>
  );
}
