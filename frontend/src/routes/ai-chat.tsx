import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Brain } from "lucide-react";
import { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/ai-chat")({
  head: () => ({
    meta: [
      { title: "AI Chat — LensEstate" },
      { name: "description", content: "Chat with the LensEstate AI assistant about properties, valuations and the market." },
    ],
  }),
  component: ChatPage,
});

type Msg = { role: "user" | "ai"; text: string };
const suggestions = [
  "What's the average price in Tunis?",
  "Best ROI areas for villas?",
  "Predict next 12 months for Sousse",
  "Show me properties under €300k",
];

function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: "Hi! I'm your LensEstate assistant. Ask me anything about properties, prices, or trends." },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  function send(text: string) {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      setMsgs((m) => [...m, { role: "ai", text: aiReply(text) }]);
      setTyping(false);
    }, 900);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <div className="flex-1 mx-auto w-full max-w-3xl px-4 py-8 flex flex-col">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gradient-primary)] glow-purple">
            <Brain className="h-5 w-5 text-white" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">AI Assistant</h1>
            <div className="text-xs text-muted-foreground flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> Online</div>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto pb-4">
          <AnimatePresence initial={false}>
            {msgs.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                  m.role === "user"
                    ? "bg-[var(--gradient-primary)] text-white"
                    : "glass"
                }`}>
                  {m.text}
                </div>
              </motion.div>
            ))}
            {typing && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex">
                <div className="glass rounded-2xl px-4 py-3 flex gap-1">
                  {[0,1,2].map(i => (
                    <span key={i} className="h-2 w-2 rounded-full bg-secondary animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {msgs.length <= 1 && (
          <div className="grid grid-cols-2 gap-2 mb-4">
            {suggestions.map((s) => (
              <button key={s} onClick={() => send(s)} className="text-left rounded-xl border border-border glass px-4 py-3 text-sm hover:border-secondary transition">
                <Sparkles className="inline h-3 w-3 gold-text mr-1.5" />{s}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="glass rounded-2xl p-2 flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about real estate…"
            className="flex-1 bg-transparent outline-none px-3 py-2 text-sm placeholder:text-muted-foreground"
          />
          <button type="submit" className="h-10 w-10 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center glow-purple hover:scale-105 transition">
            <Send className="h-4 w-4 text-white" />
          </button>
        </form>
      </div>
    </div>
  );
}

function aiReply(q: string) {
  const lower = q.toLowerCase();
  if (lower.includes("tunis")) return "The average price in Tunis is currently around €2,400 / m², up 12.4% YoY. Demand is strongest in Lac 2 and Berges du Lac.";
  if (lower.includes("roi") || lower.includes("invest")) return "Top ROI areas this quarter: Hammamet (+9.1%), Sousse (+7.8%) and select districts of Sfax. Villas with pools outperform apartments.";
  if (lower.includes("predict") || lower.includes("forecast")) return "My 12-month forecast for Sousse shows a +6.4% appreciation with 88% confidence, driven by tourism recovery and infrastructure investment.";
  return "Great question! Based on aggregated market data, I'd recommend exploring the map view to compare options. Want me to filter by price or region?";
}
