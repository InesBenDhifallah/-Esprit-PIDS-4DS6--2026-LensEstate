import React, { useState, useRef, useEffect } from "react";
 
const STATIC_USER_ID = "admin_user_test";
 
const QUICK_ACTIONS = [
  { label: "🏙️ Tunis vs Sousse", query: "Fais-moi un benchmark entre Tunis et Sousse" },
  { label: "📈 Tendances 2026", query: "Quelles sont les tendances du marché en 2026 ?" },
  { label: "💎 Meilleures zones", query: "Quelles sont les meilleures zones pour investir ?" },
];
 
const NAV_ITEMS = [
  { icon: "🔍", label: "Rechercher" },
  { icon: "🤖", label: "Estimation IA" },
  { icon: "🗺️", label: "Carte Marché" },
  { icon: "🏠", label: "Fiche Bien" },
  { icon: "💬", label: "Assistant IA", active: true },
  { icon: "💎", label: "Tarifs" },
];
 
const typingAnimation = `
  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); }
    40% { transform: translateY(-6px); }
  }
`;
 
export default function LensEstateAssistant() {
  const [messages, setMessages] = useState([{ id: "welcome-init", role: "assistant", isWelcome: true }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
 
  const messagesEndRef = useRef(null);
 
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);
 
  useEffect(() => {
    fetchHistoryList();
  }, []);
 
  const fetchHistoryList = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/get_user_sessions?user_id=${STATIC_USER_ID}`);
      const data = await response.json();
      setHistory(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Erreur historique sidebar:", error);
    }
  };
 
  const handleDownload = async () => {
    if (!currentSessionId) return;
    try {
      const response = await fetch(`http://127.0.0.1:5000/download_last_benchmark?session_id=${currentSessionId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "Rapport_LensEstate.pdf");
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        alert("Aucun rapport généré dans cette discussion.");
      }
    } catch (error) {
      console.error("Erreur:", error);
    }
  };
 
  const startNewChat = () => {
    if (loading) return;
    setCurrentSessionId(null);
    setMessages([{ id: "welcome-" + Date.now(), role: "assistant", isWelcome: true }]);
  };
 
  const loadConversation = async (sessionId) => {
    if (loading || sessionId === currentSessionId) return;
    setLoading(true);
    setCurrentSessionId(sessionId);
    try {
      const response = await fetch(`http://127.0.0.1:5000/get_conversation?session_id=${sessionId}`);
      const data = await response.json();
      if (data.messages) {
        const historyMsgs = data.messages.map((m, idx) => ({
          ...m,
          id: `msg-${sessionId}-${idx}`,
        }));
        setMessages([{ id: "welcome-" + sessionId, role: "assistant", isWelcome: true }, ...historyMsgs]);
      }
    } catch (error) {
      console.error("Erreur chargement conversation:", error);
    } finally {
      setLoading(false);
    }
  };
 
  const handleDownloadWithText = async (reportText) => {
    try {
      const response = await fetch("http://127.0.0.1:5000/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texte: reportText }),
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "Rapport_LensEstate.pdf";
        link.click();
      }
    } catch (error) {
      console.error("Erreur export PDF:", error);
    }
  };
 
  const sendMessage = async (text) => {
    const userText = text || input.trim();
    if (!userText || loading) return;
 
    let sId = currentSessionId;
    if (!sId) {
      sId = "sess_" + Date.now();
      setCurrentSessionId(sId);
    }
 
    setInput("");
    const userMsg = { id: "u-" + Date.now(), role: "user", text: userText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
 
    try {
      const response = await fetch("http://127.0.0.1:5000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userText,
          session_id: sId,
          user_id: STATIC_USER_ID,
        }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { id: "ai-" + Date.now(), role: "assistant", text: data.answer }]);
      fetchHistoryList();
    } catch {
      setMessages((prev) => [...prev, { id: "err-" + Date.now(), role: "assistant", text: "❌ Serveur déconnecté. Vérifiez votre backend Flask." }]);
    } finally {
      setLoading(false);
    }
  };
 
  return (
    <div style={styles.root}>
      <style>{typingAnimation}</style>
 
      {/* ── NAVBAR ── */}
      <nav style={styles.nav}>
        {/* Logo */}
        <div style={styles.logo}>
          {/* Remplace /logo.png par le chemin de ton image */}
          <img
            src="logo.jpeg"
            alt="LensEstate Logo"
            style={styles.logoImg}
            onError={(e) => { e.target.style.display = "none"; }}
          />
          <div style={styles.logoFallback}>

            <div>
              <div style={styles.logoName}>
                <span style={styles.logoLens}>Lens</span>
                <span style={styles.logoEstate}>Estate</span>
              </div>
              <div style={styles.logoSub}>SMART INVESTMENT SOLUTIONS</div>
            </div>
          </div>
        </div>
 
        {/* Nav links */}
        <div style={styles.navLinks}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.label}
              style={item.active ? { ...styles.navBtn, ...styles.navBtnActive } : styles.navBtn}
            >
              <span>{item.icon}</span> {item.label}
            </button>
          ))}
        </div>
 
        {/* Right side: search + icons + premium + avatar */}
        <div style={styles.navRight}>
          {/* Search */}
          <div style={styles.searchWrap}>
            <span style={styles.searchIcon}>🔍</span>
            <input style={styles.searchInput} placeholder="Chercher un bien…" />
          </div>
 
          {/* Notification bell */}
          <button style={styles.iconCircleBtn}>
            <span style={{ fontSize: 16 }}>🔔</span>
            <span style={styles.badge}>3</span>
          </button>
 
          {/* Heart / favourites */}
          <button style={styles.iconCircleBtn}>
            <span style={{ fontSize: 16 }}>❤️</span>
          </button>
 
          {/* Premium CTA */}
          <button style={styles.premiumBtn}>✦ Freemium → Premium</button>
 
          {/* User avatar */}
          <div style={styles.userAvatar}>
            <span style={{ fontSize: 18 }}>👤</span>
          </div>
        </div>
      </nav>
 
      {/* ── LAYOUT ── */}
      <div style={styles.layout}>
        {/* Sidebar */}
        <aside style={styles.sidebar}>
          <button onClick={startNewChat} style={styles.newChatBtn}>
            + Nouvelle Discussion
          </button>
          <div style={styles.sidebarHeader}>🕒 MES DISCUSSIONS</div>
          <div style={styles.historyList}>
            {history.map((item) => (
              <div
                key={item.id}
                style={{
                  ...styles.historyItem,
                  backgroundColor: currentSessionId === item.id ? "#f1f5f9" : "transparent",
                }}
                onClick={() => loadConversation(item.id)}
              >
                <div style={styles.historyText}>{item.title || "Nouvelle discussion"}</div>
                <div style={styles.historyTime}>
                  {currentSessionId === item.id ? "Session active" : "Ancienne session"}
                </div>
              </div>
            ))}
          </div>
        </aside>
 
        {/* Chat panel */}
        <div style={styles.chatPanel}>
          {/* Chat header */}
          <div style={styles.chatHeader}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
              <div style={styles.chatHeaderLeft}>
                <div style={styles.botAvatar}>🤖</div>
                <div>
                  <div style={styles.botName}>LensEstate AI Assistant</div>
                  <div style={styles.botStatus}>
                    <span style={styles.statusDot}></span> Expert Immobilier Connecté
                  </div>
                </div>
              </div>
            </div>
          </div>
 
          {/* Messages */}
          <div style={styles.messages}>
            {messages.map((msg) =>
              msg.isWelcome ? (
                <WelcomeCard key={msg.id} onSend={sendMessage} />
              ) : (
                <MessageBubble key={msg.id} msg={msg} onDownload={(text) => handleDownloadWithText(text)} />
              )
            )}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
 
          {/* Input */}
          <div style={styles.inputRow}>
            <input
              style={styles.textInput}
              placeholder="Posez votre question en français ou بالعربية…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={loading}
            />
            <button style={styles.sendBtn} onClick={() => sendMessage()} disabled={loading}>
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
 
// ── WELCOME CARD (style image 2) ──
function WelcomeCard({ onSend }) {
  const now = new Date();
  const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`;
 
  return (
    <div style={styles.welcomeWrapper}>
      <div style={styles.welcomeCard}>
        <p style={styles.welcomeArabic}>مرحباً! أنا مساعدك العقاري الذكي.</p>
        <p style={{ marginBottom: 12, fontSize: 14, lineHeight: 1.6 }}>
          Bonjour ! Je suis <strong>LensEstate AI</strong>, votre assistant immobilier tunisien. Je peux vous aider à :
        </p>
        <ul style={styles.welcomeList}>
          <li><span style={styles.featureIcon}>🔥</span> <strong>Évaluer</strong> le juste prix d'un bien</li>
          <li><span style={styles.featureIcon}>📍</span> <strong>Comparer</strong> des zones géographiques</li>
          <li><span style={styles.featureIcon}>📈</span> <strong>Analyser</strong> les tendances du marché</li>
          <li><span style={styles.featureIcon}>💎</span> <strong>Détecter</strong> des opportunités sous-évaluées</li>
          <li><span style={styles.featureIcon}>🔮</span> <strong>Prévoir</strong> les prix sur 6–12 mois</li>
        </ul>
        <p style={{ marginTop: 14, fontSize: 13, color: "#64748b" }}>Que souhaitez-vous analyser ?</p>
 
        {/* Quick suggestion chips */}
        <div style={styles.chipRow}>
          {["Prix à Sousse ?", "Investir 300K TND ?", "Tunis vs Sfax"].map((q) => (
            <button key={q} style={styles.chip} onClick={() => onSend(q)}>
              {q}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.welcomeTime}>{timeStr}</div>
    </div>
  );
}
 
// ── MESSAGE BUBBLE ──
function MessageBubble({ msg, onDownload }) {
  const isUser = msg.role === "user";
  const isReport = !isUser && (msg.text?.includes("RAPPORT") || msg.text?.includes("|"));
 
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start", marginBottom: 15 }}>
      <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", alignItems: "flex-end", gap: 8, width: "100%" }}>
        {!isUser && <div style={styles.msgAvatar}>🤖</div>}
        <div style={isUser ? { ...styles.bubble, ...styles.bubbleUser } : { ...styles.bubble, ...styles.bubbleBot }}>
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.text}</div>
        </div>
      </div>
      {isReport && (
        <button
          onClick={() => onDownload(msg.text)}
          style={styles.inlineDownloadBtn}
          onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "#244a71")}
          onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "#1a3c5e")}
        >
          📥 Télécharger le rapport complet (PDF)
        </button>
      )}
    </div>
  );
}
 
// ── TYPING INDICATOR ──
function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      <div style={styles.msgAvatar}>🤖</div>
      <div style={{ ...styles.bubble, ...styles.bubbleBot, padding: "12px 16px" }}>
        <div style={styles.typingDots}>
          <span style={{ ...styles.dot, animation: "bounce 1.2s infinite ease-in-out" }}></span>
          <span style={{ ...styles.dot, animation: "bounce 1.2s infinite ease-in-out", animationDelay: "0.2s" }}></span>
          <span style={{ ...styles.dot, animation: "bounce 1.2s infinite ease-in-out", animationDelay: "0.4s" }}></span>
        </div>
      </div>
    </div>
  );
}
 
// ── STYLES ──
const styles = {
  root: { fontFamily: "'Segoe UI', sans-serif", background: "#f3f4f6", minHeight: "100vh", display: "flex", flexDirection: "column" },
 
  /* Navbar */
  nav: { background: "#fff", borderBottom: "1px solid #e5e7eb", display: "flex", alignItems: "center", padding: "0 16px", height: 58, gap: 12, boxShadow: "0 1px 4px rgba(0,0,0,0.06)" },
 
  /* Logo */
  logo: { display: "flex", alignItems: "center", gap: 8, marginRight: 8, flexShrink: 0 },
  logoImg: { height: 40, width: "auto", borderRadius: 8, objectFit: "contain" },
  logoFallback: { display: "flex", alignItems: "center", gap: 8 },
  logoIcon: { fontSize: 22, background: "#1a3c5e", borderRadius: 8, width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center" },
  logoName: { fontWeight: 800, fontSize: 17, lineHeight: 1.1 },
  logoLens: { color: "#f59e0b" },
  logoEstate: { color: "#1a3c5e" },
  logoSub: { fontSize: 7, color: "#9ca3af", letterSpacing: 0.8 },
 
  /* Nav links */
  navLinks: { display: "flex", gap: 2, flex: 1 },
  navBtn: { background: "none", border: "none", padding: "6px 11px", cursor: "pointer", fontSize: 13, color: "#374151", borderRadius: 6, display: "flex", alignItems: "center", gap: 5 },
  navBtnActive: { background: "#1a3c5e", color: "#fff" },
 
  /* Right side */
  navRight: { display: "flex", alignItems: "center", gap: 8, flexShrink: 0 },
 
  /* Search */
  searchWrap: { display: "flex", alignItems: "center", background: "#f3f4f6", border: "1px solid #e5e7eb", borderRadius: 20, padding: "4px 14px", gap: 6 },
  searchIcon: { fontSize: 13, color: "#9ca3af" },
  searchInput: { border: "none", background: "transparent", outline: "none", fontSize: 13, width: 160, color: "#374151" },
 
  /* Icon circle buttons */
  iconCircleBtn: { position: "relative", width: 36, height: 36, borderRadius: "50%", border: "1px solid #e5e7eb", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 },
  badge: { position: "absolute", top: -4, right: -4, background: "#ef4444", color: "#fff", fontSize: 9, fontWeight: 700, width: 16, height: 16, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", border: "2px solid #fff" },
 
  /* Premium button */
  premiumBtn: { background: "#1a3c5e", color: "#fff", border: "none", borderRadius: 20, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" },
 
  /* User avatar */
  userAvatar: { width: 36, height: 36, borderRadius: "50%", background: "#1a3c5e", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 },
 
  /* Layout */
  layout: { display: "flex", flex: 1, maxHeight: "calc(100vh - 58px)" },
 
  /* Sidebar */
  sidebar: { width: 260, background: "#fff", borderRight: "1px solid #e5e7eb", display: "flex", flexDirection: "column" },
  newChatBtn: { margin: 15, padding: 10, background: "#1a3c5e", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 700, fontSize: 13 },
  sidebarHeader: { padding: "8px 20px 12px", fontSize: 11, fontWeight: 800, color: "#64748b", letterSpacing: 0.8 },
  historyList: { flex: 1, overflowY: "auto" },
  historyItem: { padding: "12px 20px", cursor: "pointer", borderBottom: "1px solid #f8fafc", transition: "0.2s" },
  historyText: { fontSize: 13, fontWeight: 600, color: "#1a3c5e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  historyTime: { fontSize: 11, color: "#94a3b8", marginTop: 2 },
 
  /* Chat panel */
  chatPanel: { flex: 1, display: "flex", flexDirection: "column", background: "#fff" },
  chatHeader: { background: "#1a3c5e", color: "#fff", padding: "12px 20px" },
  chatHeaderLeft: { display: "flex", alignItems: "center", gap: 12 },
  botAvatar: { width: 40, height: 40, background: "rgba(255,255,255,0.12)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, border: "1px solid rgba(255,255,255,0.2)" },
  botName: { fontWeight: 700, fontSize: 15 },
  botStatus: { fontSize: 12, color: "rgba(255,255,255,0.7)", display: "flex", alignItems: "center", gap: 6 },
  statusDot: { display: "inline-block", width: 8, height: 8, background: "#22c55e", borderRadius: "50%", boxShadow: "0 0 4px #22c55e" },
 
  /* Messages */
  messages: { flex: 1, overflowY: "auto", padding: "24px 20px" },
 
  /* Welcome card */
  welcomeWrapper: { marginBottom: 20, maxWidth: 560 },
  welcomeCard: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 16, padding: "20px 22px", boxShadow: "0 1px 6px rgba(0,0,0,0.05)" },
  welcomeArabic: { textAlign: "right", fontWeight: 700, direction: "rtl", fontSize: 14, color: "#1a3c5e", marginBottom: 10, borderBottom: "1px solid #f1f5f9", paddingBottom: 10 },
  welcomeList: { listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8, fontSize: 14 },
  featureIcon: { marginRight: 4 },
  chipRow: { display: "flex", gap: 6, flexWrap: "wrap", marginTop: 14 },
  chip: { background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 20, padding: "5px 12px", fontSize: 12, cursor: "pointer", color: "#1a3c5e", fontWeight: 500 },
  welcomeTime: { fontSize: 11, color: "#9ca3af", marginTop: 6, paddingLeft: 4 },
 
  /* Bubbles */
  bubble: { maxWidth: "75%", padding: "12px 16px", borderRadius: 16, fontSize: 14, boxShadow: "0 1px 2px rgba(0,0,0,0.05)" },
  bubbleBot: { background: "#f1f5f9", border: "1px solid #e2e8f0", color: "#1e293b" },
  bubbleUser: { background: "#1a3c5e", color: "#fff", marginLeft: "auto" },
  msgAvatar: { width: 32, height: 32, background: "#1a3c5e", borderRadius: "50%", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 },
 
  /* Input */
  inputRow: { display: "flex", padding: "16px 20px", borderTop: "1px solid #e5e7eb", gap: 10, background: "#fff" },
  textInput: { flex: 1, padding: "12px 20px", borderRadius: 24, border: "1px solid #e2e8f0", outline: "none", fontSize: 14 },
  sendBtn: { width: 44, height: 44, background: "#f97316", border: "none", borderRadius: "50%", color: "#fff", cursor: "pointer", fontSize: 20, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 },
 
  /* Typing */
  typingDots: { display: "flex", gap: 4, height: 10, alignItems: "center" },
  dot: { width: 6, height: 6, background: "#94a3b8", borderRadius: "50%" },
 
  /* Download */
  inlineDownloadBtn: {
    marginTop: 10,
    marginLeft: 42,
    backgroundColor: "#1a3c5e",
    color: "white",
    border: "none",
    padding: "10px 18px",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    display: "flex",
    alignItems: "center",
    gap: 8,
    transition: "background-color 0.2s ease",
    boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
  },
  
};