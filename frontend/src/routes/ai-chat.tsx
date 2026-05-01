import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Brain, Download } from "lucide-react";
import { useEffect, useState } from "react";
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

type Msg = { id?: number; role: "user" | "ai"; text: string; showReportDownload?: boolean };
const suggestions = [
  "What's the average price in Tunis?",
  "Best ROI areas for villas?",
  "Predict next 12 months for Sousse",
  "Show me properties under €300k",
];

function ChatPage() {
  const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const [sessionId] = useState(() => crypto.randomUUID());
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: "Hi! I'm your LensEstate assistant. Ask me anything about properties, prices, or trends." },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [lastBenchmarkAnswer, setLastBenchmarkAnswer] = useState<string | null>(null);

  useEffect(() => {
    async function loadConversation() {
      try {
        const response = await fetch(`${API_BASE}/api/chat/get_conversation/?session_id=${sessionId}`);
        if (!response.ok) return;
        const data = await response.json();
        if (!Array.isArray(data.messages) || data.messages.length === 0) return;
        const mapped: Msg[] = data.messages.map((m: { id: number; role: string; text: string }) => ({
          id: m.id,
          role: m.role === "assistant" ? "ai" : "user",
          text: m.text,
        }));
        setMsgs(mapped);
      } catch {
        // Keep local greeting if backend chat history is unavailable
      }
    }
    void loadConversation();
  }, [API_BASE, sessionId]);

  async function send(text: string) {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setTyping(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat/ask/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          session_id: sessionId,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Chat service error");

      const isBenchmark = /rapport|benchmark|comparer|comparaison|comparison/i.test(text);
      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: isBenchmark
            ? "Ce document contient les details de la comparaison entre les 2 regions que vous avez citees."
            : (data.answer ?? "Aucune reponse recue."),
          showReportDownload: isBenchmark,
        },
      ]);

      if (isBenchmark) {
        setLastBenchmarkAnswer(data.answer ?? "");
      }
    } catch (error) {
      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: error instanceof Error ? error.message : "Le service chatbot est indisponible.",
        },
      ]);
    } finally {
      setTyping(false);
    }
  }

  async function downloadBenchmarkReport() {
    if (!lastBenchmarkAnswer) return;
    const res = await fetch(`${API_BASE}/api/chat/generate-pdf/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texte: lastBenchmarkAnswer }),
    });
    if (!res.ok) return;

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Rapport_LensEstate.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
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
                  <p>{m.text}</p>
                  {m.showReportDownload && (
                    <button
                      type="button"
                      onClick={downloadBenchmarkReport}
                      className="mt-3 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:border-secondary transition"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Telecharger le rapport
                    </button>
                  )}
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

