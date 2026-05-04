import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, LayoutGrid, Sparkles, Plus, Trash2, Download, Home, Info } from "lucide-react";
import { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/plan-generator")({
  head: () => ({
    meta: [
      { title: "2D Plan Generator — LensEstate" },
      { name: "description", content: "Generate 2D floor plans from your inputs in seconds with AI." },
    ],
  }),
  component: PlanPage,
});

const ROOM_TYPES = [
  "living_room", "kitchen", "bedroom", "bathroom", "closet", "balcony", "corridor", "dining_room", "laundry_room"
];

function PlanPage() {
  const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8005";
  const [rooms, setRooms] = useState<string[]>(["living_room", "kitchen", "bedroom"]);
  const [edges, setEdges] = useState<number[][]>([[0, 1], [0, 2]]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const addRoom = (type: string = "bedroom") => {
    setRooms([...rooms, type]);
  };

  const removeRoom = (index: number) => {
    const newRooms = rooms.filter((_, i) => i !== index);
    const newEdges = edges.filter(([u, v]) => u !== index && v !== index)
      .map(([u, v]) => [
        u > index ? u - 1 : u, 
        v > index ? v - 1 : v
      ]);
    setRooms(newRooms);
    setEdges(newEdges);
  };

  const toggleEdge = (u: number, v: number) => {
    const exists = edges.find(([eU, eV]) => (eU === u && eV === v) || (eU === v && eV === u));
    if (exists) {
      setEdges(edges.filter(e => e !== exists));
    } else {
      setEdges([...edges, [u, v]]);
    }
  };

  const generatePlan = async () => {
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rooms, edges }),
      });
      
      if (!response.ok) throw new Error("Generation failed");
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setResult(url);
    } catch (error) {
      console.error("Generation failed", error);
      alert("Error generating plan. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h1 className="mt-2 text-4xl md:text-5xl font-bold">2D Floor Plan AI</h1>
          <p className="mt-3 text-muted-foreground">Define your room connections and let our Relational GAN draft the layout.</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Configuration Panel */}
          <div className="space-y-6">
            <div className="rounded-2xl glass p-6 space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <LayoutGrid className="h-5 w-5 gold-text" /> 
                  Room Configuration
                </h3>
              </div>

              {/* Quick Add */}
              <div className="flex flex-wrap gap-2">
                {["living_room", "corridor", "bathroom", "kitchen", "room"].map(type => (
                  <button 
                    key={type}
                    onClick={() => addRoom(type === "room" ? "bedroom" : type)}
                    className="text-[10px] uppercase tracking-wider px-2 py-1 rounded bg-secondary/10 text-secondary border border-secondary/20 hover:bg-secondary/20 transition"
                  >
                    + {type.replace('_', ' ')}
                  </button>
                ))}
              </div>

              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                {rooms.map((room, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3 bg-surface/30 rounded-xl p-3 border border-border"
                  >
                    <div className="h-7 w-7 rounded-full bg-[var(--gradient-primary)] flex items-center justify-center text-xs font-bold text-white shadow-sm">
                      {i}
                    </div>
                    <select 
                      value={room} 
                      onChange={(e) => {
                        const next = [...rooms];
                        next[i] = e.target.value;
                        setRooms(next);
                      }}
                      className="flex-1 bg-transparent border-none outline-none text-sm cursor-pointer"
                    >
                      {ROOM_TYPES.map(rt => (
                        <option key={rt} value={rt} className="bg-slate-900">
                          {rt.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </option>
                      ))}
                    </select>
                    <button onClick={() => removeRoom(i)} className="text-muted-foreground hover:text-red-400 transition">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </motion.div>
                ))}
              </div>

              <div className="pt-4 border-t border-border">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
                  Adjacency (Connect rooms)
                </h4>
                <div className="flex flex-wrap gap-2">
                  {rooms.map((_, i) => (
                    rooms.map((_, j) => {
                      if (j <= i) return null;
                      const connected = edges.find(([u, v]) => (u === i && v === j) || (u === j && v === i));
                      return (
                        <button 
                          key={`${i}-${j}`}
                          onClick={() => toggleEdge(i, j)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                            connected 
                              ? "bg-secondary/20 text-secondary border border-secondary/50 shadow-[0_0_10px_rgba(var(--secondary-rgb),0.2)]" 
                              : "bg-surface/30 border border-border text-muted-foreground hover:border-muted"
                          }`}
                        >
                          {i} ↔ {j}
                        </button>
                      );
                    })
                  ))}
                </div>
              </div>

              <div className="bg-secondary/5 border border-secondary/20 rounded-xl p-4 flex gap-3">
                <Info className="h-5 w-5 text-secondary shrink-0" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                  <strong className="text-secondary">Tip:</strong> Connect rooms to a <strong>Corridor</strong> to help the AI structure the layout and avoid overlaps.
                </p>
              </div>

              <button 
                onClick={generatePlan}
                disabled={loading || rooms.length === 0}
                className="w-full rounded-xl bg-[var(--gradient-primary)] py-4 text-sm font-semibold text-white glow-purple inline-flex items-center justify-center gap-2 hover:scale-[1.01] transition disabled:opacity-50"
              >
                {loading ? (
                  <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <><Sparkles className="h-5 w-5" /> Generate Variations</>
                )}
              </button>
            </div>
          </div>

          {/* Result Panel */}
          <div className="rounded-2xl glass p-6 min-h-[500px] flex flex-col">
            <AnimatePresence mode="wait">
              {!result && !loading && (
                <motion.div 
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 flex flex-col items-center justify-center text-center space-y-4"
                >
                  <div className="h-20 w-20 rounded-full bg-surface/50 flex items-center justify-center border border-border">
                    <Home className="h-10 w-10 text-muted-foreground opacity-30" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Ready to draft</h3>
                    <p className="text-sm text-muted-foreground max-w-[250px] mx-auto">
                      Configure your rooms on the left and click generate to see the AI proposals.
                    </p>
                  </div>
                </motion.div>
              )}

              {loading && (
                <motion.div 
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 flex flex-col items-center justify-center text-center space-y-6"
                >
                  <div className="relative">
                    <div className="h-16 w-16 border-4 border-secondary/20 border-t-secondary rounded-full animate-spin" />
                    <Sparkles className="h-6 w-6 text-secondary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                  </div>
                  <p className="text-sm text-muted-foreground animate-pulse">Calculating spatial relations...</p>
                </motion.div>
              )}

              {result && !loading && (
                <motion.div 
                  key="result"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex-1 flex flex-col space-y-6"
                >
                  <div className="flex-1 bg-surface/20 rounded-2xl border border-border p-4 overflow-hidden relative group">
                    <img src={result} alt="Generated Plan" className="w-full h-full object-contain rounded-lg" />
                    <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                      <p className="text-[10px] text-white/80 text-center uppercase tracking-widest">AI Generated Layout (3 Variations)</p>
                    </div>
                  </div>
                  
                  <div className="flex gap-3 justify-center">
                    <a 
                      href={result} 
                      download="lensestate-floorplan.png"
                      className="rounded-xl border border-border glass px-6 py-2.5 text-sm font-medium hover:border-secondary transition flex items-center gap-2"
                    >
                      <Download className="h-4 w-4" /> Download PNG
                    </a>
                    <button 
                      onClick={() => setResult(null)}
                      className="rounded-xl px-6 py-2.5 text-sm font-medium bg-surface/50 border border-border hover:bg-surface/80 transition"
                    >
                      Reset
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
