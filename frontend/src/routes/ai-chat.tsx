import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Send, Sparkles, Brain, Download, 
  MessageSquare, Plus, History, 
  ChevronLeft, Menu, Lock
} from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { useAuth } from "@/context/AuthContext";
import { get, post } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

export const Route = createFileRoute("/ai-chat")({
  head: () => ({
    meta: [
      { title: "AI Chat — LensEstate" },
      { name: "description", content: "Chat with the LensEstate AI assistant about properties, valuations and the market." },
    ],
  }),
  component: ChatPage,
});

type Msg = {
  id?: number;
  role: "user" | "ai";
  text: string;
  showReportDownload?: boolean;
  downloadLabel?: string;
};

type Session = {
  id: string;
  title: string;
};

const BENCHMARK_PREFIX_STOP = new Set([
  "benchmarking", "benchmark", "comparison", "comparaison", "comparer", "compare", "rapport", "report",
  "the", "la", "le", "les", "un", "une", "des", "de", "du", "entre", "between", "and", "et", "of", "pour", "with"
]);

function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/\p{M}/gu, "");
}

function normalizeToken(w: string): string {
  return stripDiacritics(w).toLowerCase().replace(/[^a-z0-9-]/g, "");
}

function stripFillerWords(chunk: string): string {
  const words = chunk.trim().split(/\s+/).filter(Boolean);
  while (words.length && BENCHMARK_PREFIX_STOP.has(normalizeToken(words[0]))) words.shift();
  while (words.length && BENCHMARK_PREFIX_STOP.has(normalizeToken(words[words.length - 1]))) words.pop();
  return words.join(" ").trim();
}

function titleCaseRegion(s: string): string {
  if (!s) return s;
  return s.split(/\s+/).map((w) => (w.length <= 2 ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())).join(" ");
}

function detectQuestionLang(question: string): "fr" | "en" | "ar" {
  if (/[\u0600-\u06FF]/.test(question)) return "ar";
  if (/[àâäéèêëïîôùûüç]/i.test(question)) return "fr";
  const lower = question.toLowerCase();
  const frScore = /\b(entre|et|comparaison|comparer|régions?|villes?|télécharger|telecharger|details|détails)\b/i.test(lower) ? 2 : 0;
  const enScore = /\b(between|and|comparison|compare|regions?|cities?|download|details)\b/i.test(lower) ? 2 : 0;
  if (frScore > enScore) return "fr";
  if (enScore > frScore) return "en";
  return "en";
}

function extractTwoRegions(question: string): [string, string] | null {
  let q = question.trim();
  q = q.replace(/بين\s+(.+?)\s+و\s+(.+)/i, "$1, $2");
  q = q.replace(/\bentre\s+(.+?)\s+et\s+(.+)/i, "$1, $2");
  q = q.replace(/\bbetween\s+(.+?)\s+and\s+(.+)/i, "$1, $2");
  const commaParts = q.split(",").map((p) => stripFillerWords(p)).filter(Boolean);
  if (commaParts.length >= 2) return [titleCaseRegion(commaParts[commaParts.length - 2]), titleCaseRegion(commaParts[commaParts.length - 1])];
  return null;
}

function benchmarkIntro(lang: "fr" | "en" | "ar", regions: [string, string] | null): string {
  const [r1, r2] = regions ?? [];
  if (r1 && r2) {
    if (lang === "ar") return `هذا التقرير يلخص المقارنة بين ${r1} و ${r2}.`;
    if (lang === "fr") return `Ce document résume la comparaison entre ${r1} et ${r2}.`;
    return `This document summarizes the comparison between ${r1} and ${r2}.`;
  }
  if (lang === "ar") return "يحتوي هذا المستند على تفاصيل المقارنة بين المنطقتين.";
  if (lang === "fr") return "Ce document résume la comparaison entre les deux régions indiquées.";
  return "This document contains the comparison details for the two regions you mentioned.";
}

function benchmarkDownloadLabel(lang: "fr" | "en" | "ar"): string {
  if (lang === "ar") return "تحميل التقرير";
  if (lang === "fr") return "Télécharger le rapport";
  return "Download report";
}

const SUGGESTIONS = [
  "What's the average price in Tunis?",
  "Best ROI areas for villas?",
  "Predict next 12 months for Sousse",
  "Show me properties under €300k",
];

function ChatPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => localStorage.getItem("last_chat_session_id"));
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "ai", text: "Hi! I'm your LensEstate assistant. Ask me anything about properties, prices, or trends." }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [lastBenchmarkAnswer, setLastBenchmarkAnswer] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (isAuthenticated) void fetchSessions(); }, [isAuthenticated]);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs, typing]);
  useEffect(() => { if (isAuthenticated && currentSessionId) { void loadConversation(currentSessionId); localStorage.setItem("last_chat_session_id", currentSessionId); } }, [isAuthenticated, currentSessionId]);

  async function fetchSessions() {
    try { const data = await get<Session[]>("/api/chat/get_user_sessions/"); setSessions(data); } catch (e) { console.error(e); }
  }

  async function loadConversation(sid: string) {
    try {
      const data = await get<{ messages: any[] }>(`/api/chat/get_conversation/?session_id=${sid}`);
      if (data.messages && data.messages.length > 0) {
        setMsgs(data.messages.map(m => ({ role: m.role === "assistant" ? "ai" : "user", text: m.text })));
      } else {
        setMsgs([{ role: "ai", text: "New conversation started. How can I help you today?" }]);
      }
    } catch (e) { console.error(e); }
  }

  async function startNewChat() {
    const newId = crypto.randomUUID();
    setCurrentSessionId(newId);
    setMsgs([{ role: "ai", text: "New conversation started. How can I help you today?" }]);
    if (window.innerWidth < 1024) setSidebarOpen(false);
  }

  async function send(text: string) {
    if (!text.trim() || !isAuthenticated) return;
    let sid = currentSessionId || crypto.randomUUID();
    if (!currentSessionId) setCurrentSessionId(sid);

    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setTyping(true);

    const isBenchmark = /rapport|benchmark|comparer|comparaison|comparison|compare|report|مقارنة|تقرير|قارن|بنشمارك/i.test(text);
    const lang = detectQuestionLang(text);
    const regions = isBenchmark ? extractTwoRegions(text) : null;

    try {
      const data = await post<{ answer: string }>("/api/chat/ask/", { question: text, session_id: sid });
      
      const intro = isBenchmark ? benchmarkIntro(lang, regions) : "";
      const downloadLabel = isBenchmark ? benchmarkDownloadLabel(lang) : undefined;
      const answerBody = data.answer || (lang === "fr" ? "Aucune réponse." : "No response.");

      setMsgs((m) => [...m, { 
        role: "ai", 
        text: isBenchmark ? intro : answerBody,
        showReportDownload: isBenchmark,
        downloadLabel
      }]);
      
      if (isBenchmark) setLastBenchmarkAnswer(data.answer);
      if (!sessions.find(s => s.id === sid)) void fetchSessions();
    } catch (error: any) {
      setMsgs((m) => [...m, { role: "ai", text: `Error: ${error.message}` }]);
    } finally {
      setTyping(false);
    }
  }

  async function downloadBenchmarkReport() {
    if (!lastBenchmarkAnswer) return;
    try {
      const token = getAccessToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/chat/generate-pdf/`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json", 
          "Authorization": token ? `Bearer ${token}` : "" 
        },
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
    } catch (e) { console.error(e); }
  }

  if (authLoading) return <div className="h-screen flex items-center justify-center">Loading...</div>;

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="max-w-md w-full glass p-8 rounded-3xl text-center space-y-6">
            <div className="mx-auto h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center"><Lock className="h-8 w-8 text-primary" /></div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold">Connectez-vous pour discuter</h2>
              <p className="text-muted-foreground">Votre historique de discussions sera sauvegardé sur votre compte.</p>
            </div>
            <Link to="/auth" className="block w-full py-4 rounded-2xl bg-[var(--gradient-primary)] text-white font-bold hover:opacity-90 transition">Se connecter / Créer un compte</Link>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      <SiteHeader />
      <div className="flex-1 flex overflow-hidden relative">
        <motion.aside initial={false} animate={{ width: sidebarOpen ? 280 : 0, opacity: sidebarOpen ? 1 : 0 }} className="bg-surface/40 border-r border-border overflow-hidden flex flex-col z-20">
          <div className="p-4 border-b border-border"><button onClick={startNewChat} className="w-full flex items-center gap-2 px-4 py-3 rounded-xl bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors font-medium text-sm"><Plus className="h-4 w-4" /> New Chat</button></div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-bold flex items-center gap-2"><History className="h-3 w-3" /> Recent History</div>
            {sessions.map(s => (
              <button key={s.id} onClick={() => { setCurrentSessionId(s.id); if (window.innerWidth < 1024) setSidebarOpen(false); }} className={`w-full text-left px-3 py-3 rounded-xl text-sm transition-all group flex items-center gap-3 ${currentSessionId === s.id ? "bg-primary/10 text-primary border border-primary/10" : "hover:bg-muted text-muted-foreground"}`}>
                <MessageSquare className={`h-4 w-4 shrink-0 ${currentSessionId === s.id ? "text-primary" : "text-muted-foreground/50"}`} />
                <span className="truncate">{s.title || "Untitled Chat"}</span>
              </button>
            ))}
          </div>
        </motion.aside>

        <main className="flex-1 flex flex-col relative overflow-hidden">
          <div className="h-14 border-b border-border flex items-center justify-between px-4 bg-surface/20 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground">{sidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
              <div className="flex items-center gap-2"><Brain className="h-4 w-4 text-primary" /><span className="font-semibold text-sm">LensEstate AI</span></div>
            </div>
            <div className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /><span className="text-[10px] font-medium text-muted-foreground">READY</span></div>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
            <AnimatePresence initial={false}>
              {msgs.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 10, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`group relative max-w-[85%] rounded-2xl px-5 py-3 text-sm shadow-sm ${m.role === "user" ? "bg-[var(--gradient-primary)] text-white" : "glass border-border/50"}`}>
                    <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>
                    {m.showReportDownload && (
                      <button type="button" onClick={downloadBenchmarkReport} className="mt-3 flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:border-primary transition bg-surface/50">
                        <Download className="h-3.5 w-3.5" /> {m.downloadLabel || "Download report"}
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
              {typing && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex">
                  <div className="glass rounded-2xl px-5 py-3 flex gap-1.5 items-center">
                    {[0, 1, 2].map(i => <span key={i} className="h-1.5 w-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            {msgs.length <= 1 && (
              <div className="grid sm:grid-cols-2 gap-3 mt-8">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="text-left rounded-2xl border border-border glass p-4 text-sm hover:border-primary/50 hover:bg-primary/5 transition-all group">
                    <div className="flex items-center gap-2 mb-1"><Sparkles className="h-3.5 w-3.5 text-amber-500" /><span className="text-[10px] font-bold text-muted-foreground group-hover:text-primary transition-colors uppercase tracking-wider">Suggestion</span></div>{s}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="p-4 border-t border-border bg-surface/40 backdrop-blur-md">
            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="max-w-3xl mx-auto glass rounded-2xl p-2 flex items-center gap-2 focus-within:border-primary/50 transition-colors">
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask LensEstate assistant..." className="flex-1 bg-transparent outline-none px-4 py-2.5 text-sm placeholder:text-muted-foreground" />
              <button type="submit" disabled={!input.trim() || typing} className="h-10 w-10 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center glow-purple hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100"><Send className="h-4 w-4 text-white" /></button>
            </form>
            <p className="text-[10px] text-center mt-2 text-muted-foreground/60">LensEstate AI can make mistakes. Check important info.</p>
          </div>
        </main>
      </div>

      <style>{`
        .glass { background: color-mix(in oklab, var(--surface) 70%, transparent); backdrop-filter: blur(12px); border: 1px solid var(--border); }
        .glow-purple { box-shadow: 0 0 20px -5px hsl(var(--primary) / 0.5); }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
      `}</style>
    </div>
  );
}
