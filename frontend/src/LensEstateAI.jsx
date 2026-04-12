import { useState, useRef, useEffect } from "react";

const QUICK_ACTIONS = [
  { label: "🏙️ Tunis vs Sousse", query: "Fais-moi un benchmark entre Tunis et Sousse" },
  { label: "📈 Tendances 2026", query: "Quelles sont les tendances du marché en 2026 ?" },
  { label: "💎 Meilleures zones", query: "Quelles sont les meilleures zones pour investir ?" },
  { label: "🏠 Avantages Ezzahra", query: "Quels sont les avantages et inconvénients de vivre à Ezzahra ?" },
];

const NAV_ITEMS = [
  { icon: "🔍", label: "Rechercher" },
  { icon: "🤖", label: "Estimation IA" },
  { icon: "🗺️", label: "Carte Marché" },
  { icon: "🏠", label: "Fiche Bien" },
  { icon: "💬", label: "Assistant IA", active: true },
  { icon: "💎", label: "Tarifs" },
];

const WELCOME_MESSAGE = {
  id: 0,
  role: "assistant",
  text: null,
  isWelcome: true,
};

export default function LensEstateAssistant() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text) => {
    const userText = text || input.trim();
    if (!userText || loading) return;
    setInput("");

    const userMsg = { id: Date.now(), role: "user", text: userText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      // Connexion auserveur Flask 
      const response = await fetch("http://127.0.0.1:5000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userText }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: "assistant", text: data.answer }]);
    } catch {
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: "assistant", text: "❌ Le serveur LensEstate est hors ligne. Veuillez lancer votre script Python." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.root}>
      {/* TOP NAV */}
      <nav style={styles.nav}>
        <div style={styles.logo}>
          <div style={styles.logoIcon}>🏘️</div>
          <div>
            <div style={styles.logoName}><span style={styles.logoLens}>Lens</span><span style={styles.logoEstate}>Estate</span></div>
            <div style={styles.logoSub}>SMART INVESTMENT SOLUTIONS</div>
          </div>
        </div>
        <div style={styles.navLinks}>
          {NAV_ITEMS.map((item) => (
            <button key={item.label} style={item.active ? { ...styles.navBtn, ...styles.navBtnActive } : styles.navBtn}>
              <span>{item.icon}</span> {item.label}
            </button>
          ))}
        </div>
        <div style={styles.navRight}>
          <button style={styles.premiumBtn}>✦ Freemium → Premium</button>
          <div style={styles.avatar}>👤</div>
        </div>
      </nav>

      {/* MAIN LAYOUT */}
      <div style={styles.layout}>
        <div style={styles.chatPanel}>
          <div style={styles.chatHeader}>
            <div style={styles.chatHeaderLeft}>
              <div style={styles.botAvatar}>🤖</div>
              <div>
                <div style={styles.botName}>LensEstate AI Assistant</div>
                <div style={styles.botStatus}><span style={styles.statusDot}></span> Expert Immobilier Connecté</div>
              </div>
            </div>
          </div>

          <div style={styles.messages}>
            {messages.map((msg) =>
              msg.isWelcome ? <WelcomeCard key={msg.id} /> : <MessageBubble key={msg.id} msg={msg} />
            )}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          <div style={styles.quickActions}>
            {QUICK_ACTIONS.map((a) => (
              <button key={a.label} style={styles.quickBtn} onClick={() => sendMessage(a.query)}>
                {a.label}
              </button>
            ))}
          </div>

          <div style={styles.inputRow}>
            <input
              style={styles.textInput}
              placeholder="Posez votre question sur l'immobilier..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={loading}
            />
            <button style={styles.sendBtn} onClick={() => sendMessage()} disabled={loading}>↑</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function WelcomeCard() {
  return (
    <div style={styles.welcomeCard}>
      <p style={styles.welcomeArabic}>مرحباً بك في منصة LensEstate</p>
      <p style={{ marginBottom: 15, fontSize: "16px" }}>
        Bonjour <strong>Cher Investisseur</strong> ! Je suis votre assistant expert dédié au marché immobilier tunisien.
      </p>
      <div style={{ background: "#f8fafc", padding: "15px", borderRadius: "8px", borderLeft: "4px solid #1a3c5e" }}>
        <p style={{ fontWeight: "600", marginBottom: "10px", color: "#1a3c5e" }}>Voici comment je peux vous accompagner :</p>
        <ul style={styles.welcomeList}>
          <li>🔍 <strong>Analyse de Zones</strong> : Tendances, avantages et inconvénients par quartier.</li>
          <li>📊 <strong>Benchmarking</strong> : Comparaison des prix et loyers selon vos préférences.</li>
          <li>📈 <strong>Expertise Marché</strong> : Analyse approfondie des tendances actuelles.</li>
          <li>💎 <strong>Suggestions de Biens</strong> : Recommandations d'annonces adaptées à votre profil.</li>
        </ul>
      </div>
      <p style={{ marginTop: 15, color: "#64748b", fontStyle: "italic" }}>Quelle zone ou quel type d'investissement souhaitez-vous explorer aujourd'hui ?</p>
    </div>
  );
}


function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      <div style={styles.msgAvatar}>🤖</div>
      <div style={{ ...styles.bubble, ...styles.bubbleBot, padding: "12px 16px" }}>
        <div style={styles.typingDots}>
          <span style={{ ...styles.dot, animationDelay: "0s" }}></span>
          <span style={{ ...styles.dot, animationDelay: "0.2s" }}></span>
          <span style={{ ...styles.dot, animationDelay: "0.4s" }}></span>
        </div>
      </div>
      <style>{`@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }`}</style>
    </div>
  );
}
function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  const isBenchmark = !isUser && msg.text?.includes("BENCHMARKING");

  const downloadPDF = async () => {
    const response = await fetch("http://127.0.0.1:5000/generate-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texte: msg.text }),
    });
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Rapport_LensEstate.pdf";
    a.click();
  };

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: 12 }}>
      {!isUser && <div style={styles.msgAvatar}>🤖</div>}
      <div style={isUser ? { ...styles.bubble, ...styles.bubbleUser } : { ...styles.bubble, ...styles.bubbleBot }}>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.text}</div>
        {isBenchmark && (
          <button onClick={downloadPDF} style={styles.pdfBtn}>
            📄 Télécharger PDF
          </button>
        )}
      </div>
    </div>
  );
}

const styles = {
  root: { fontFamily: "'Segoe UI', sans-serif", background: "#f3f4f6", minHeight: "100vh", display: "flex", flexDirection: "column" },
  nav: { background: "#fff", borderBottom: "1px solid #e5e7eb", display: "flex", alignItems: "center", padding: "0 20px", height: 56, gap: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.07)" },
  logo: { display: "flex", alignItems: "center", gap: 10, marginRight: 16 },
  logoIcon: { fontSize: 28, background: "#1a3c5e", borderRadius: 8, width: 40, height: 40, display: "flex", alignItems: "center", justifyContent: "center" },
  logoName: { fontWeight: 800, fontSize: 18, lineHeight: 1.1 },
  logoLens: { color: "#f59e0b" },
  logoEstate: { color: "#1a3c5e" },
  logoSub: { fontSize: 8, color: "#6b7280", letterSpacing: 1 },
  navLinks: { display: "flex", gap: 2, flex: 1 },
  navBtn: { background: "none", border: "none", cursor: "pointer", padding: "6px 12px", borderRadius: 6, fontSize: 13, color: "#374151", display: "flex", alignItems: "center", gap: 5 },
  navBtnActive: { background: "#1a3c5e", color: "#fff" },
  navRight: { display: "flex", alignItems: "center", gap: 10 },
  premiumBtn: { background: "#1a3c5e", color: "#fff", border: "none", borderRadius: 20, padding: "5px 14px", fontSize: 12, cursor: "pointer", whiteSpace: "nowrap" },
  avatar: { width: 34, height: 34, borderRadius: "50%", background: "#e5e7eb", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 },
  layout: { display: "flex", flex: 1, justifyContent: "center", maxHeight: "calc(100vh - 56px)" },
  chatPanel: { width: "100%", maxWidth: "1000px", display: "flex", flexDirection: "column", background: "#fff", boxShadow: "0 0 15px rgba(0,0,0,0.05)" },
  chatHeader: { background: "#1a3c5e", color: "#fff", padding: "12px 20px" },
  chatHeaderLeft: { display: "flex", alignItems: "center", gap: 12 },
  botAvatar: { width: 40, height: 40, background: "rgba(255,255,255,0.15)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 },
  botName: { fontWeight: 700, fontSize: 15 },
  botStatus: { fontSize: 12, color: "#94a3b8", display: "flex", alignItems: "center", gap: 6 },
  statusDot: { width: 8, height: 8, background: "#22c55e", borderRadius: "50%" },
  messages: { flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column" },
  welcomeCard: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20, maxWidth: "600px", alignSelf: "center", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" },
  welcomeArabic: { textAlign: "right", color: "#1a3c5e", fontWeight: 700, fontSize: 15, marginBottom: 8 },
  welcomeList: { listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8, fontSize: 14 },
  bubble: { maxWidth: "75%", padding: "12px 16px", borderRadius: 16, fontSize: 14 },
  bubbleBot: { background: "#f1f5f9", border: "1px solid #e2e8f0", borderTopLeftRadius: 4 },
  bubbleUser: { background: "#1a3c5e", color: "#fff", borderTopRightRadius: 4 },
  msgAvatar: { width: 32, height: 32, background: "#1a3c5e", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 },
  typingDots: { display: "flex", gap: 4 },
  dot: { width: 8, height: 8, background: "#94a3b8", borderRadius: "50%", animation: "bounce 1.2s infinite ease-in-out" },
  quickActions: { display: "flex", gap: 8, padding: "10px 16px", flexWrap: "wrap", justifyContent: "center" },
  quickBtn: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 20, padding: "6px 14px", fontSize: 12, cursor: "pointer", color: "#475569" },
  inputRow: { display: "flex", gap: 10, padding: "15px 20px", borderTop: "1px solid #e5e7eb" },
  textInput: { flex: 1, border: "1px solid #e2e8f0", borderRadius: 24, padding: "10px 20px", fontSize: 14, outline: "none" },
  sendBtn: { width: 40, height: 40, background: "#f97316", border: "none", borderRadius: "50%", color: "#fff", cursor: "pointer" },
  pdfBtn: {
  marginTop: 12,
  background: "#1a3c5e",
  color: "#fff",
  border: "none",
  borderRadius: 20,
  padding: "7px 18px",
  fontSize: 13,
  cursor: "pointer",
  display: "block",
}
};