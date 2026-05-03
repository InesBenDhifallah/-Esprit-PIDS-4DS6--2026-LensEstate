import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Brain, Download, Plus, MessageSquare } from "lucide-react";
import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { apiRequest } from "@/lib/api";

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
  "benchmarking", "benchmark", "comparison", "comparaison", "comparer",
  "compare", "rapport", "report", "the", "la", "le", "les", "un", "une",
  "des", "de", "du", "entre", "between", "and", "et", "of", "pour", "with",
]);

const GOVERNORATS_TN = new Set([
  "tunis", "ariana", "ben arous", "manouba", "nabeul", "zaghouan",
  "bizerte", "beja", "jendouba", "kef", "siliana", "sousse",
  "monastir", "mahdia", "sfax", "kairouan", "kasserine", "sidi bouzid",
  "gabes", "mednine", "tataouine", "gafsa", "tozeur", "kebili",
  "تونس", "أريانة", "بن عروس", "منوبة", "نابل", "زغوان",
  "بنزرت", "باجة", "جندوبة", "الكاف", "سليانة", "سوسة",
  "المنستير", "المهدية", "صفاقس", "القيروان", "القصرين", "سيدي بوزيد",
  "قابس", "مدنين", "تطاوين", "قفصة", "توزر", "قبلي"
]);

function isGovernorat(name: string): boolean {
  return GOVERNORATS_TN.has(name.toLowerCase().trim());
}

function clarificationMessage(lang: "fr" | "en" | "ar", regions: [string, string]): string {
  const [r1, r2] = regions;
  if (lang === "ar") return `للمقارنة الدقيقة، يرجى تحديد منطقة من كل ولاية:\n- منطقة من ${r1}\n- منطقة من ${r2}`;
  if (lang === "fr") return `Pour une comparaison précise, veuillez préciser une région de chaque gouvernorat :\n- Une région de ${r1} (ex: Centre-ville, Corniche...)\n- Une région de ${r2} (ex: Centre-ville, Corniche...)`;
  return `For a precise comparison, please specify a region from each governorate:\n- A region from ${r1} (e.g: Downtown, Suburb...)\n- A region from ${r2} (e.g: Downtown, Suburb...)`;
}

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
  if (/\b(je|vous|pour|avec|sont|est|une|des|les)\b/i.test(lower)) return "fr";
  return "en";
}

function extractTwoRegions(question: string): [string, string] | null {
  let q = question.trim();
  q = q.replace(/بين\s+(.+?)\s+و\s+(.+)/i, "$1, $2");
  q = q.replace(/\bentre\s+(.+?)\s+et\s+(.+)/i, "$1, $2");
  q = q.replace(/\bbetween\s+(.+?)\s+and\s+(.+)/i, "$1, $2");

  const commaParts = q.split(",").map((p) => stripFillerWords(p)).filter(Boolean);
  if (commaParts.length >= 2) {
    const a = commaParts[commaParts.length - 2];
    const b = commaParts[commaParts.length - 1];
    if (a && b) return [titleCaseRegion(a), titleCaseRegion(b)];
  }

  const normalized = q.replace(/\bbetween\b/gi, " and ").replace(/\bet\b/gi, " and ").replace(/\band\b/gi, " and ");
  const andParts = normalized.split(/\s+and\s+/i).map((p) => stripFillerWords(p)).filter(Boolean);
  if (andParts.length >= 2) {
    const a = andParts[andParts.length - 2];
    const b = andParts[andParts.length - 1];
    if (a && b) return [titleCaseRegion(a), titleCaseRegion(b)];
  }
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

const suggestions = [
  "What's the average price in Tunis?",
  "Best ROI areas for villas?",
  "Predict next 12 months for Sousse",
  "Show me properties under €300k",
];

function ChatPage() {
  const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: "Hi! I'm your LensEstate assistant. Ask me anything about properties, prices, or trends." },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [lastBenchmarkAnswer, setLastBenchmarkAnswer] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);

  // Charge les sessions de l'utilisateur
  async function loadSessions() {
    try {
      const data = await apiRequest<Session[]>("/api/chat/get_user_sessions/");
      setSessions(data);
    } catch {
      // utilisateur non connecté
    }
  }

  useEffect(() => {
    void loadSessions();
  }, []);

  useEffect(() => {
    async function loadConversation() {
      try {
        const data = await apiRequest<{ messages: { id: number; role: string; text: string }[] }>(
          `/api/chat/get_conversation/?session_id=${sessionId}`
        );
        if (!Array.isArray(data.messages) || data.messages.length === 0) return;
        const mapped: Msg[] = data.messages.map((m) => ({
          id: m.id,
          role: m.role === "assistant" ? "ai" : "user",
          text: m.text,
        }));
        setMsgs(mapped);
      } catch {
        // Keep local greeting
      }
    }
    void loadConversation();
  }, [sessionId]);

  function newChat() {
    setSessionId(crypto.randomUUID());
    setMsgs([{ role: "ai", text: "Hi! I'm your LensEstate assistant. Ask me anything about properties, prices, or trends." }]);
    setLastBenchmarkAnswer(null);
  }

  async function loadSession(id: string) {
    setSessionId(id);
    setMsgs([]);
  }

  async function send(text: string) {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setTyping(true);

    const isBenchmark = /rapport|benchmark|comparer|comparaison|comparison|compare|report|مقارنة|تقرير|قارن|بنشمارك/i.test(text);
    const lang = detectQuestionLang(text);
    const regions = isBenchmark ? extractTwoRegions(text) : null;

    if (isBenchmark && regions) {
      const [r1, r2] = regions;
      if (isGovernorat(r1) || isGovernorat(r2)) {
        setTyping(false);
        setMsgs((m) => [...m, { role: "ai", text: clarificationMessage(lang, regions) }]);
        return;
      }
    }

    try {
      const data = await apiRequest<{ answer: string }>("/api/chat/ask/", {
        method: "POST",
        body: JSON.stringify({ question: text, session_id: sessionId }),
      });

      const intro = isBenchmark ? benchmarkIntro(lang, regions) : "";
      const downloadLabel = isBenchmark ? benchmarkDownloadLabel(lang) : undefined;
      const answerBody = data.answer ?? (lang === "fr" ? "Aucune réponse reçue." : "No response received.");

      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: isBenchmark ? intro : answerBody,
          showReportDownload: isBenchmark,
          downloadLabel,
        },
      ]);

      if (isBenchmark) setLastBenchmarkAnswer(data.answer ?? "");

      // Recharge les sessions après un nouveau message
      void loadSessions();

    } catch (error) {
      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: error instanceof Error ? error.message : lang === "fr" ? "Le service chatbot est indisponible." : "The chatbot service is unavailable.",
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
      <div className="flex-1 flex overflow-hidden">

        {/* Sidebar */}
        <div className="w-64 border-r border-border glass flex flex-col p-3 gap-2">
          <button
            onClick={newChat}
            className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm hover:border-secondary transition w-full"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
          <div className="text-xs text-muted-foreground px-1 mt-2">History</div>
          <div className="flex-1 overflow-y-auto space-y-1">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => loadSession(s.id)}
                className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:border-secondary transition w-full text-left truncate ${s.id === sessionId ? "border border-secondary" : "border border-transparent"
                  }`}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{s.title}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 mx-auto w-full max-w-3xl px-4 py-8 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gradient-primary)] glow-purple">
              <Brain className="h-5 w-5 text-white" />
            </span>
            <div>
              <h1 className="text-lg font-semibold">AI Assistant</h1>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> Online
              </div>
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
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "bg-[var(--gradient-primary)] text-white" : "glass"
                    }`}>
                    <p>{m.text}</p>
                    {m.showReportDownload && (
                      <button
                        type="button"
                        onClick={downloadBenchmarkReport}
                        className="mt-3 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:border-secondary transition"
                      >
                        <Download className="h-3.5 w-3.5" />
                        {m.downloadLabel ?? "Download report"}
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
              {typing && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex">
                  <div className="glass rounded-2xl px-4 py-3 flex gap-1">
                    {[0, 1, 2].map(i => (
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
    </div>
  );
}