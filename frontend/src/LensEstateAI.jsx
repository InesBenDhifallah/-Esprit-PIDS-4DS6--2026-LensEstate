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

// Animation CSS pour les points de chargement
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

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Chargement initial de l'historique
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
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Rapport_LensEstate.pdf`);
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
    // Sécurité : ne pas recharger si on est déjà sur cette session ou si ça charge déjà
    if (loading || sessionId === currentSessionId) return;

    setLoading(true);
    setCurrentSessionId(sessionId);
    try {
      const response = await fetch(`http://127.0.0.1:5000/get_conversation?session_id=${sessionId}`);
      const data = await response.json();
      
      if (data.messages) {
        // On reconstruit proprement le tableau de messages avec des IDs uniques
        const historyMsgs = data.messages.map((m, idx) => ({
          ...m,
          id: `msg-${sessionId}-${idx}`
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
      const link = document.createElement('a');
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

    // Déterminer l'ID de session actuel ou en créer un nouveau
    let sId = currentSessionId;
    if (!sId) {
      sId = "sess_" + Date.now();
      setCurrentSessionId(sId);
    }

    setInput(""); // Vider le champ immédiatement
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
            user_id: STATIC_USER_ID 
        }),
      });
      const data = await response.json();
      
      setMessages((prev) => [...prev, { 
        id: "ai-" + Date.now(), 
        role: "assistant", 
        text: data.answer 
      }]);
      
      // Rafraîchir la sidebar pour mettre à jour les titres
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
      </nav>

      <div style={styles.layout}>
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
                    backgroundColor: currentSessionId === item.id ? "#f1f5f9" : "transparent"
                }} 
                onClick={() => loadConversation(item.id)}
              >
                <div style={styles.historyText}>{item.title || "Nouvelle discussion"}</div>
                <div style={styles.historyTime}>{currentSessionId === item.id ? "Session active" : "Ancienne session"}</div>
              </div>
            ))}
          </div>
        </aside>

        <div style={styles.chatPanel}>
          <div style={styles.chatHeader}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <div style={styles.chatHeaderLeft}>
                  <div style={styles.botAvatar}>🤖</div>
                  <div>
                    <div style={styles.botName}>LensEstate AI Assistant</div>
                    <div style={styles.botStatus}><span style={styles.statusDot}></span> Expert Immobilier Connecté</div>
                  </div>
                </div>
                
              </div>
            </div>

          <div style={styles.messages}>
            {messages.map((msg) =>
              msg.isWelcome ? (
                <WelcomeCard key={msg.id} />
              ) : (
                <MessageBubble 
                  key={msg.id} 
                  msg={msg} 
                  onDownload={(text) => handleDownloadWithText(text)} 
                />
              )
            )}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
</div>

          <div style={styles.inputRow}>
            <input
              style={styles.textInput}
              placeholder="Posez votre question..."
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

// --- SOUS-COMPOSANTS ---

function WelcomeCard() {
  return (
    <div style={styles.welcomeCard}>
      <p style={styles.welcomeArabic}>مرحباً بك في منصة LensEstate</p>
      <p style={{ marginBottom: 15, fontSize: "16px" }}>
        Bonjour ! Je suis votre assistant expert du marché immobilier tunisien.
      </p>
      <div style={{ background: "#f8fafc", padding: "15px", borderRadius: "8px", borderLeft: "4px solid #1a3c5e" }}>
        <ul style={styles.welcomeList}>
          <li>🔍 <strong>Analyse</strong> : Tendances et prix par quartier.</li>
          <li>📊 <strong>Benchmark</strong> : Comparaison de zones.</li>
        </ul>
      </div>
    </div>
  );
}

function MessageBubble({ msg, onDownload }) {
  const isUser = msg.role === "user";
  // On détecte si c'est un rapport de benchmark via le titre ou la structure Markdown [cite: 8, 9]
  const isReport = !isUser && (msg.text?.includes("RAPPORT") || msg.text?.includes("|"));

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start", marginBottom: 15 }}>
      <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", width: "100%" }}>
        {!isUser && <div style={styles.msgAvatar}>🤖</div>}
        <div style={isUser ? { ...styles.bubble, ...styles.bubbleUser } : { ...styles.bubble, ...styles.bubbleBot }}>
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.text}</div>
        </div>
      </div>

      {/* BOUTON BLEU THÈME LENSESTATE */}
      {isReport && (
        <button 
          onClick={() => onDownload(msg.text)} 
          style={styles.inlineDownloadBtn}
          onMouseOver={(e) => e.target.style.backgroundColor = "#244a71"}
          onMouseOut={(e) => e.target.style.backgroundColor = "#1a3c5e"}
        >
          📥 Télécharger le rapport complet (PDF)
        </button>
      )}
    </div>
  );
}

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

// --- STYLES ---
const styles = {
  root: { fontFamily: "'Segoe UI', sans-serif", background: "#f3f4f6", minHeight: "100vh", display: "flex", flexDirection: "column" },
  nav: { background: "#fff", borderBottom: "1px solid #e5e7eb", display: "flex", alignItems: "center", padding: "0 20px", height: 56, gap: 16 },
  logo: { display: "flex", alignItems: "center", gap: 10 },
  logoIcon: { fontSize: 28, background: "#1a3c5e", borderRadius: 8, width: 40, height: 40, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" },
  logoName: { fontWeight: 800, fontSize: 18 },
  logoLens: { color: "#f59e0b" },
  logoEstate: { color: "#1a3c5e" },
  logoSub: { fontSize: 8, color: "#6b7280" },
  navLinks: { display: "flex", gap: 2, flex: 1 },
  navBtn: { background: "none", border: "none", padding: "6px 12px", cursor: "pointer", fontSize: 13 },
  navBtnActive: { background: "#1a3c5e", color: "#fff", borderRadius: 6 },
  layout: { display: "flex", flex: 1, maxHeight: "calc(100vh - 56px)" },
  sidebar: { width: "260px", background: "#fff", borderRight: "1px solid #e5e7eb", display: "flex", flexDirection: "column" },
  newChatBtn: { margin: "15px", padding: "10px", background: "#1a3c5e", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "bold" },
  sidebarHeader: { padding: "15px 20px", fontSize: "12px", fontWeight: "800", color: "#64748b" },
  historyList: { flex: 1, overflowY: "auto" },
  historyItem: { padding: "12px 20px", cursor: "pointer", borderBottom: "1px solid #f8fafc", transition: "0.2s" },
  historyText: { fontSize: "13px", fontWeight: "600", color: "#1a3c5e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  historyTime: { fontSize: "11px", color: "#94a3b8" },
  chatPanel: { flex: 1, display: "flex", flexDirection: "column", background: "#fff" },
  chatHeader: { background: "#1a3c5e", color: "#fff", padding: "12px 20px" },
  chatHeaderLeft: { display: "flex", alignItems: "center", gap: 12 },
  botAvatar: { width: 40, height: 40, background: "rgba(255,255,255,0.1)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" },
  botName: { fontWeight: 700 },
  botStatus: { fontSize: 12 },
  statusDot: { display: "inline-block", width: 8, height: 8, background: "#22c55e", borderRadius: "50%" },
  messages: { flex: 1, overflowY: "auto", padding: "20px" },
  welcomeCard: { border: "1px solid #e5e7eb", borderRadius: 12, padding: 20, maxWidth: "600px", margin: "0 auto", marginBottom: 20 },
  welcomeArabic: { textAlign: "right", fontWeight: 700, direction: "rtl" },
  welcomeList: { listStyle: "none", padding: 0 },
  bubble: { maxWidth: "75%", padding: "12px 16px", borderRadius: 16, fontSize: 14, boxShadow: "0 1px 2px rgba(0,0,0,0.05)" },
  bubbleBot: { background: "#f1f5f9", border: "1px solid #e2e8f0", color: "#1e293b" },
  bubbleUser: { background: "#1a3c5e", color: "#fff", marginLeft: "auto" },
  msgAvatar: { width: 32, height: 32, background: "#1a3c5e", borderRadius: "50%", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 },
  quickActions: { display: "flex", gap: 8, padding: "10px", justifyContent: "center", flexWrap: "wrap" },
  quickBtn: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 20, padding: "6px 12px", fontSize: 12, cursor: "pointer", transition: "0.2s" },
  inputRow: { display: "flex", padding: "20px", borderTop: "1px solid #e5e7eb", gap: 10, background: "#fff" },
  textInput: { flex: 1, padding: "12px 20px", borderRadius: 24, border: "1px solid #e2e8f0", outline: "none" },
  sendBtn: { width: 42, height: 42, background: "#f97316", border: "none", borderRadius: "50%", color: "#fff", cursor: "pointer", fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center" },
  typingDots: { display: "flex", gap: 4, height: "10px", alignItems: "center" },
  dot: { width: 6, height: 6, background: "#94a3b8", borderRadius: "50%" },

  inlineDownloadBtn: {
    marginTop: "10px",
    marginLeft: "42px", // Aligné après l'avatar du robot
    backgroundColor: "#1a3c5e", // Bleu du thème LensEstate
    color: "white",
    border: "none",
    padding: "10px 18px",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    transition: "background-color 0.2s ease",
    boxShadow: "0 2px 5px rgba(0,0,0,0.1)"
  },
};