import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp } from "lucide-react";
import { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/price-prediction")({
  head: () => ({
    meta: [
      { title: "Price Prediction — LensEstate" },
      { name: "description", content: "Get an instant AI valuation with confidence and explanation." },
    ],
  }),
  component: PredictPage,
});

function PredictPage() {
  const [result, setResult] = useState<null | { price: number; conf: number }>(null);

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="text-center max-w-2xl mx-auto">
          <span className="text-xs uppercase tracking-widest gold-text font-semibold">AI Tool</span>
          <h1 className="mt-2 text-4xl md:text-5xl font-bold">Price Prediction</h1>
          <p className="mt-3 text-muted-foreground">Estimate any property's fair value in seconds.</p>
        </div>

        <div className="mt-12 grid lg:grid-cols-2 gap-8">
          <div className="rounded-2xl glass p-6 space-y-4">
            <Field label="Region">
              <select className="w-full rounded-xl border border-border bg-surface/50 px-4 py-2.5 text-sm">
                <option>Tunis</option><option>Sousse</option><option>Sfax</option><option>Hammamet</option>
              </select>
            </Field>
            <Field label="Property type">
              <select className="w-full rounded-xl border border-border bg-surface/50 px-4 py-2.5 text-sm">
                <option>Villa</option><option>Apartment</option><option>Penthouse</option>
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Surface (m²)"><input type="number" defaultValue={180} className="input" /></Field>
              <Field label="Year built"><input type="number" defaultValue={2018} className="input" /></Field>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Beds"><input type="number" defaultValue={3} className="input" /></Field>
              <Field label="Baths"><input type="number" defaultValue={2} className="input" /></Field>
              <Field label="Pool"><select className="input"><option>No</option><option>Yes</option></select></Field>
            </div>
            <button
              onClick={() => setResult({ price: 412000, conf: 89 })}
              className="w-full rounded-xl bg-[var(--gradient-primary)] py-3 text-sm font-medium text-white glow-purple inline-flex items-center justify-center gap-2"
            >
              <Sparkles className="h-4 w-4" /> Predict price
            </button>
          </div>

          <motion.div
            key={result ? "r" : "e"}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl p-6 relative overflow-hidden"
            style={{ background: result ? "var(--gradient-primary)" : "transparent" }}
          >
            {result ? (
              <>
                <div className="absolute inset-0 opacity-30" style={{ background: "var(--gradient-hero)" }} />
                <div className="relative text-white">
                  <div className="text-xs text-white/80 uppercase tracking-widest flex items-center gap-2"><Sparkles className="h-3.5 w-3.5 gold-text" /> AI Estimate</div>
                  <div className="mt-2 text-5xl font-bold">€{result.price.toLocaleString()}</div>
                  <div className="mt-1 text-sm text-white/70">±€18,000 range</div>

                  <div className="mt-6 grid grid-cols-2 gap-4">
                    <div className="rounded-xl bg-white/10 p-4">
                      <div className="text-xs text-white/70">Confidence</div>
                      <div className="text-2xl font-bold gold-text">{result.conf}%</div>
                    </div>
                    <div className="rounded-xl bg-white/10 p-4">
                      <div className="text-xs text-white/70">Market trend</div>
                      <div className="text-2xl font-bold flex items-center gap-1"><TrendingUp className="h-5 w-5" />+7.2%</div>
                    </div>
                  </div>

                  <div className="mt-6">
                    <h4 className="text-sm font-semibold">Explanation</h4>
                    <ul className="mt-2 space-y-1.5 text-sm text-white/85 list-disc list-inside">
                      <li>Comparable villas in Sousse average €2,290/m²</li>
                      <li>Pool & build year add a +5% premium</li>
                      <li>Recent transactions support an 89% confidence band</li>
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full glass rounded-2xl flex items-center justify-center text-muted-foreground text-sm p-8 min-h-[300px]">
                Fill the form and run a prediction to see the result.
              </div>
            )}
          </motion.div>
        </div>
      </div>
      <style>{`.input { width:100%; border-radius: 0.75rem; border:1px solid var(--border); background: color-mix(in oklab, var(--surface) 50%, transparent); padding:.625rem 1rem; font-size: .875rem; outline: none; }`}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}
