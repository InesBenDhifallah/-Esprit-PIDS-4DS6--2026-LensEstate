import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Upload, LayoutGrid, Sparkles } from "lucide-react";
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

function PlanPage() {
  const [generated, setGenerated] = useState(false);

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="text-center max-w-2xl mx-auto">
          <span className="text-xs uppercase tracking-widest gold-text font-semibold">AI Tool</span>
          <h1 className="mt-2 text-4xl md:text-5xl font-bold">2D Plan Generator</h1>
          <p className="mt-3 text-muted-foreground">Describe your space — we'll draft a clean floor plan instantly.</p>
        </div>

        <div className="mt-12 grid lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="rounded-2xl glass p-6">
              <h3 className="font-semibold mb-3">Upload reference (optional)</h3>
              <label className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-surface/40 px-6 py-12 cursor-pointer hover:border-secondary transition">
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div className="mt-3 text-sm">Drag & drop or click to upload</div>
                <div className="text-xs text-muted-foreground mt-1">PNG, JPG, PDF up to 10MB</div>
                <input type="file" className="hidden" />
              </label>
            </div>

            <div className="rounded-2xl glass p-6 space-y-4">
              <h3 className="font-semibold">Specifications</h3>
              <Input label="Total surface (m²)" placeholder="e.g. 120" />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Bedrooms" placeholder="3" />
                <Input label="Bathrooms" placeholder="2" />
              </div>
              <Input label="Style" placeholder="Modern, open-plan…" />
              <button onClick={() => setGenerated(true)} className="w-full rounded-xl bg-[var(--gradient-primary)] py-3 text-sm font-medium text-white glow-purple inline-flex items-center justify-center gap-2 hover:scale-[1.02] transition">
                <Sparkles className="h-4 w-4" /> Generate plan
              </button>
            </div>
          </div>

          <div className="rounded-2xl glass p-6 min-h-[500px] flex items-center justify-center">
            {!generated ? (
              <div className="text-center text-muted-foreground">
                <LayoutGrid className="h-12 w-12 mx-auto opacity-40" />
                <p className="mt-3 text-sm">Your generated plan will appear here</p>
              </div>
            ) : (
              <motion.svg
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                viewBox="0 0 400 300"
                className="w-full h-auto"
              >
                <rect x="10" y="10" width="380" height="280" fill="none" stroke="oklch(0.78 0.14 85)" strokeWidth="3" />
                <line x1="10" y1="150" x2="220" y2="150" stroke="oklch(0.48 0.22 290)" strokeWidth="2" />
                <line x1="220" y1="10" x2="220" y2="290" stroke="oklch(0.48 0.22 290)" strokeWidth="2" />
                <line x1="220" y1="180" x2="390" y2="180" stroke="oklch(0.48 0.22 290)" strokeWidth="2" />
                <text x="100" y="85" fill="oklch(0.92 0.01 280)" fontSize="14">Living Room</text>
                <text x="100" y="225" fill="oklch(0.92 0.01 280)" fontSize="14">Kitchen</text>
                <text x="280" y="95" fill="oklch(0.92 0.01 280)" fontSize="14">Bedroom 1</text>
                <text x="280" y="240" fill="oklch(0.92 0.01 280)" fontSize="14">Bath</text>
              </motion.svg>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Input({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <input {...props} className="mt-1 w-full rounded-xl border border-border bg-surface/50 px-4 py-2.5 text-sm outline-none focus:border-secondary" />
    </div>
  );
}
