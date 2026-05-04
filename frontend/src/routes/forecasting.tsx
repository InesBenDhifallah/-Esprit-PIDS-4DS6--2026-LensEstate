import { createFileRoute } from "@tanstack/react-router";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { TrendingUp, MapPin, Bot, Sparkles, Activity } from "lucide-react";
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
      { title: "Market Forecasting & AI Analyst — LensEstate" },
    ],
  }),
  component: ForecastPage,
});

type ForecastPoint = { m: string; price: number | null; forecast: number; };
type ForecastRegionGrowth = { name: string; growth: number; };
type ForecastResponse = {
  region: string; current_avg: number; forecast_12m: number; confidence: number;
  projected_growth_pct: number; series: ForecastPoint[]; regions: ForecastRegionGrowth[];
};
type AgentReport = { top_region: string; market_summary: string; investment_recommendation: string; };

function TiltCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const mouseX = useSpring(x, { stiffness: 400, damping: 30 });
  const mouseY = useSpring(y, { stiffness: 400, damping: 30 });
  const rotateX = useTransform(mouseY, [-100, 100], [7, -7]);
  const rotateY = useTransform(mouseX, [-100, 100], [-7, 7]);

  function onMouseMove(event: React.MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set(event.clientX - rect.left - rect.width / 2);
    y.set(event.clientY - rect.top - rect.height / 2);
  }
  function onMouseLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <motion.div
      style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      className={`relative perspective-1000 ${className}`}
    >
      <div style={{ transform: "translateZ(30px)" }} className="w-full h-full">
        {children}
      </div>
    </motion.div>
  );
}

function TypewriterText({ text, delay = 0 }: { text: string; delay?: number }) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    let i = 0;
    const timeout = setTimeout(() => {
      const interval = setInterval(() => {
        setDisplayed(text.substring(0, i));
        i++;
        if (i > text.length) clearInterval(interval);
      }, 20);
      return () => clearInterval(interval);
    }, delay);
    return () => clearTimeout(timeout);
  }, [text, delay]);
  return <span>{displayed}</span>;
}

function ForecastPage() {
  const [region, setRegion] = useState("Tunis");
  const [seriesData, setSeriesData] = useState<ForecastPoint[]>([]);
  const [regionsData, setRegionsData] = useState<ForecastRegionGrowth[]>([]);
  const [kpis, setKpis] = useState({ currentAvg: 0, forecast12m: 0, confidence: 0, growth: 0 });
  const [agentReport, setAgentReport] = useState<AgentReport | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      try {
        const data = await get<ForecastResponse>(`/api/forecasting/?region=${encodeURIComponent(region)}`, { skipAuth: true });
        if (cancelled) return;
        setSeriesData(data.series); setRegionsData(data.regions);
        setKpis({ currentAvg: data.current_avg, forecast12m: data.forecast_12m, confidence: data.confidence, growth: data.projected_growth_pct });
      } catch (e) { console.error(e); }

      try {
        const report = await get<AgentReport>(`/api/forecasting/agent/`, { skipAuth: true });
        if (!cancelled && report) setAgentReport(report);
      } catch (e) { console.error(e); }
    }
    void loadData();
    return () => { cancelled = true; };
  }, [region]);

  const growthText = useMemo(() => `${kpis.growth >= 0 ? "+" : ""}${kpis.growth}% projected`, [kpis.growth]);

  return (
    <div className="min-h-screen bg-[var(--background)] overflow-hidden relative flex flex-col">
      <SiteHeader />
      
      <main className="mx-auto max-w-7xl px-6 py-12 relative z-10 flex-1 w-full">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="flex flex-wrap items-end justify-between gap-4 mb-10">
          <div>
            <span className="text-sm uppercase tracking-widest agent-text font-bold flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> Market Intelligence 3.0
            </span>
            <h1 className="mt-2 text-5xl md:text-6xl font-extrabold tracking-tight text-white drop-shadow-lg">
              Smart <span className="gold-text">Forecasting</span>
            </h1>
            <p className="mt-3 text-lg text-muted-foreground max-w-xl">
              Powered by advanced SARIMAX modeling and autonomous AI agents to give you the ultimate real estate edge.
            </p>
          </div>
        </motion.div>

        {/* AI Agent Panel */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.2 }}
          className="mb-12 rounded-3xl p-[1px] bg-gradient-to-r from-[oklch(0.48_0.22_290)] via-[oklch(0.78_0.14_85)] to-[oklch(0.7_0.15_220)] glow-cyan"
        >
          <div className="rounded-3xl glass p-8 h-full w-full relative overflow-hidden bg-[oklch(0.21_0.02_280/0.9)]">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[oklch(0.7_0.15_220)] to-transparent opacity-50" />
            <div className="flex items-start gap-6">
              <div className="hidden sm:flex h-16 w-16 rounded-2xl bg-[var(--surface-elevated)] items-center justify-center glow-gold flex-shrink-0">
                <Bot className="w-8 h-8 text-[oklch(0.78_0.14_85)]" />
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold agent-text mb-4 flex items-center gap-2">
                  LensEstate AI Analyst
                  <span className="flex h-3 w-3 relative ml-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[oklch(0.7_0.15_220)] opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-[oklch(0.7_0.15_220)]"></span>
                  </span>
                </h2>
                
                {agentReport ? (
                  <div className="space-y-4 text-[oklch(0.92_0.01_280)] leading-relaxed text-lg">
                    <p className="font-medium">
                      <TypewriterText text={agentReport.market_summary} delay={500} />
                    </p>
                    <div className="p-4 rounded-xl bg-[var(--surface-elevated)] border border-[oklch(0.78_0.14_85/0.3)] shadow-[0_0_15px_oklch(0.78_0.14_85/0.1)]">
                      <div className="text-sm text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-2">
                        <Activity className="w-4 h-4 gold-text" /> AI Recommendation
                      </div>
                      <TypewriterText text={agentReport.investment_recommendation} delay={3000} />
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 text-muted-foreground animate-pulse">
                    <Bot className="w-5 h-5" /> Analyzing regional market data...
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Region Selector */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-hide">
          {regionsData.map((r) => (
            <button key={r.name} onClick={() => setRegion(r.name)} 
              className={`whitespace-nowrap rounded-full border px-6 py-2.5 text-sm font-semibold transition-all duration-300 ${region === r.name ? "border-[oklch(0.7_0.15_220)] bg-[oklch(0.7_0.15_220/0.15)] text-white glow-cyan scale-105" : "border-border text-muted-foreground hover:border-[oklch(0.78_0.14_85/0.5)] hover:text-white"}`}>
              {r.name}
            </button>
          ))}
        </div>

        {/* 3D KPI Cards */}
        <div className="mt-4 grid lg:grid-cols-3 gap-8">
          <TiltCard>
            <KPI label="Current Avg Price" value={`TND ${kpis.currentAvg.toLocaleString()}/m²`} sub="Updated by SARIMAX" delay={0.3} />
          </TiltCard>
          <TiltCard>
            <KPI label="12-Month Forecast" value={`TND ${kpis.forecast12m.toLocaleString()}/m²`} sub={growthText} highlight delay={0.4} />
          </TiltCard>
          <TiltCard>
            <KPI label="Model Confidence" value={`${kpis.confidence}%`} sub="Data Reliability" cyan delay={0.5} />
          </TiltCard>
        </div>

        {/* Charts */}
        <div className="mt-12 grid lg:grid-cols-3 gap-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.6 }} className="lg:col-span-2 rounded-3xl glass p-8 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-b from-[oklch(0.48_0.22_290/0.05)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
            <div className="flex items-center justify-between mb-6 relative z-10">
              <h2 className="text-xl font-bold flex items-center gap-2 text-white">
                <MapPin className="h-5 w-5 text-[oklch(0.7_0.15_220)] animate-bounce" /> {region} Trend Analysis
              </h2>
              <span className="px-3 py-1 rounded-full bg-[var(--surface-elevated)] text-xs text-muted-foreground border border-border">TND / m²</span>
            </div>
            <div className="h-[350px] w-full relative z-10">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={seriesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="oklch(0.48 0.22 290)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="oklch(0.48 0.22 290)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="oklch(0.78 0.14 85)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="oklch(0.7 0.15 220)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.3 0.03 285 / 0.2)" vertical={false} />
                  <XAxis dataKey="m" stroke="oklch(0.71 0.015 280)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="oklch(0.71 0.015 280)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `${val / 1000}k`} />
                  <Tooltip 
                    contentStyle={{ background: "rgba(26,26,34,0.9)", border: "1px solid oklch(0.48 0.22 290/0.5)", borderRadius: 16, backdropFilter: "blur(12px)", color: "#fff" }} 
                    itemStyle={{ color: "#E5E7EB" }}
                  />
                  <Area type="monotone" dataKey="price" name="Historique" stroke="oklch(0.48 0.22 290)" fill="url(#g1)" strokeWidth={3} activeDot={{ r: 6, fill: "oklch(0.48 0.22 290)", stroke: "#fff", strokeWidth: 2 }} />
                  <Area type="monotone" dataKey="forecast" name="Prédiction" stroke="oklch(0.78 0.14 85)" fill="url(#g2)" strokeWidth={3} strokeDasharray="5 5" activeDot={{ r: 6, fill: "oklch(0.78 0.14 85)", stroke: "#fff", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.8 }} className="rounded-3xl glass p-8 flex flex-col">
            <h2 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-[oklch(0.78_0.14_85)]" /> Regional Growth Map
            </h2>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={regionsData} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.3 0.03 285 / 0.2)" horizontal={true} vertical={false} />
                  <XAxis type="number" stroke="oklch(0.71 0.015 280)" fontSize={12} tickLine={false} axisLine={false} unit="%" />
                  <YAxis dataKey="name" type="category" stroke="oklch(0.92 0.01 280)" fontSize={13} tickLine={false} axisLine={false} width={80} />
                  <Tooltip cursor={{ fill: 'oklch(0.3 0.03 285 / 0.2)' }} contentStyle={{ background: "rgba(26,26,34,0.9)", border: "1px solid oklch(0.78 0.14 85/0.5)", borderRadius: 12, color: "#fff" }} />
                  <Bar dataKey="growth" radius={[0, 6, 6, 0]} barSize={20}>
                    {regionsData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.growth > 0 ? "oklch(0.78 0.14 85)" : "oklch(0.62 0.22 25)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

function KPI({ label, value, sub, highlight, cyan, delay }: { label: string; value: string; sub: string; highlight?: boolean; cyan?: boolean; delay: number }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay }}
      className={`relative rounded-3xl p-8 h-full overflow-hidden transition-all duration-300
        ${highlight ? "bg-gradient-to-br from-[oklch(0.32_0.15_285)] to-[oklch(0.48_0.22_290)] glow-purple border border-[oklch(0.48_0.22_290/0.5)]" 
        : cyan ? "glass border-[oklch(0.7_0.15_220/0.4)] glow-cyan" 
        : "glass border-[oklch(0.78_0.14_85/0.3)] shadow-[0_10px_30px_rgba(0,0,0,0.5)]"}`}
    >
      {highlight && <div className="absolute top-[-50px] right-[-50px] w-32 h-32 bg-white/10 rounded-full blur-2xl" />}
      {cyan && <div className="absolute bottom-[-30px] left-[-30px] w-24 h-24 bg-[oklch(0.7_0.15_220/0.2)] rounded-full blur-xl" />}
      
      <div className={`text-sm uppercase tracking-widest font-semibold ${highlight ? "text-white/80" : cyan ? "text-[oklch(0.7_0.15_220)]" : "gold-text"}`}>{label}</div>
      <div className={`mt-3 text-4xl font-extrabold tracking-tight ${highlight ? "text-white drop-shadow-md" : "text-white"}`}>{value}</div>
      <div className={`mt-3 text-sm flex items-center gap-2 ${highlight ? "text-white/90" : "text-muted-foreground"}`}>
        <TrendingUp className={`h-4 w-4 ${highlight ? "text-white" : cyan ? "text-[oklch(0.7_0.15_220)]" : "gold-text"}`} /> {sub}
      </div>
    </motion.div>
  );
}
