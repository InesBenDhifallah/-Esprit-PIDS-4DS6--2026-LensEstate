import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);

  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!email || !password) {
      alert("Veuillez remplir tous les champs");
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // ✅ Sauvegarde user_id dans localStorage
        localStorage.setItem("user_id", data.user_id);
        console.log("✅ Login OK - user_id sauvegardé:", data.user_id);
        // ✅ Redirection vers chatbot
        navigate("/");
      } else {
        alert(data.message || "Email ou mot de passe incorrect");
      }
    } catch (error) {
      console.error("Erreur login:", error);
      alert("Erreur serveur backend");
    }
  };

  return (
    <div style={S.page}>
      <div style={S.card}>

        {/* LEFT */}
        <div style={S.left}>
          <div style={S.logo}>
            <span style={{ fontWeight: 700 }}>LensEstate</span>
          </div>

          <h2 style={S.title}>Welcome back</h2>
          <p style={S.subtitle}>
            Connecte-toi pour accéder à ton espace immobilier intelligent.
          </p>

          <input
            style={S.input}
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          />

          <input
            style={S.input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          />

          <div style={S.row}>
            <label style={S.checkbox}>
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              Remember me
            </label>
            <button style={S.link}>Forgot password?</button>
          </div>

          <button style={S.button} onClick={handleLogin}>
            Sign in
          </button>

          <p style={S.footerText}>
            Don't have an account? <span style={S.link}>Sign up</span>
          </p>
        </div>

        {/* RIGHT */}
        <div style={S.right}>
          <div style={S.glow}></div>
          <h1 style={S.brand}>LensEstate</h1>
          <p style={S.tagline}>Smart Real Estate AI Platform</p>
          <div style={S.circle}></div>
          <div style={S.circle2}></div>
        </div>

      </div>
    </div>
  );
}

const S = {
  page: {
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "Inter, sans-serif",
    background:
      "radial-gradient(circle at top left, #1e3a8a20, transparent 40%)," +
      "radial-gradient(circle at bottom right, #c9a84c20, transparent 40%)," +
      "#0b1220",
  },
  card: {
    width: "900px",
    height: "550px",
    display: "flex",
    borderRadius: "25px",
    overflow: "hidden",
    boxShadow: "0 30px 90px rgba(0,0,0,0.4)",
  },
  left: {
    flex: 1,
    background: "rgba(255,255,255,0.95)",
    padding: "50px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
  },
  right: {
    flex: 1,
    background: "linear-gradient(145deg, #0a2463, #1e56d0)",
    color: "white",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
    overflow: "hidden",
  },
  logo: { marginBottom: 20, fontSize: 18 },
  title: { fontSize: 28, marginBottom: 5, color: "#0a2463" },
  subtitle: { fontSize: 13, color: "#6b7280", marginBottom: 25 },
  input: {
    padding: "12px",
    marginBottom: 12,
    borderRadius: 10,
    border: "1px solid #e5e7eb",
    outline: "none",
    fontSize: 14,
    background: "#f9fafb",
    width: "100%",
    boxSizing: "border-box",
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 5,
    marginBottom: 20,
  },
  checkbox: {
    fontSize: 12,
    color: "#6b7280",
    display: "flex",
    gap: 6,
    alignItems: "center",
  },
  link: {
    fontSize: 12,
    color: "#1e56d0",
    cursor: "pointer",
    background: "none",
    border: "none",
  },
  button: {
    padding: "12px",
    border: "none",
    borderRadius: 10,
    background: "linear-gradient(135deg, #1e56d0, #0a2463)",
    color: "white",
    fontWeight: "bold",
    cursor: "pointer",
    fontSize: 15,
    width: "100%",
  },
  footerText: { marginTop: 15, fontSize: 12, color: "#6b7280", textAlign: "center" },
  brand: { fontSize: 36, fontWeight: "bold" },
  tagline: { fontSize: 12, opacity: 0.8, marginTop: 10 },
  circle: {
    position: "absolute",
    width: 200,
    height: 200,
    borderRadius: "50%",
    background: "rgba(255,255,255,0.1)",
    top: -50,
    right: -50,
  },
  circle2: {
    position: "absolute",
    width: 150,
    height: 150,
    borderRadius: "50%",
    background: "rgba(255,255,255,0.08)",
    bottom: -40,
    left: -40,
  },
  glow: {
    position: "absolute",
    width: 300,
    height: 300,
    background: "rgba(255,255,255,0.05)",
    borderRadius: "50%",
    filter: "blur(40px)",
  },
};