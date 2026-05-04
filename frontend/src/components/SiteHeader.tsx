import { Link } from "@tanstack/react-router";
import { Menu, X, Mic, MicOff, Volume2 } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useAccessibility } from "@/context/AccessibilityContext";
import logo from "../assets/logo.png";

const links = [
  { to: "/", label: "Home" },
  { to: "/map", label: "Explore" },
  { to: "/ai-chat", label: "AI Chat" },
  { to: "/price-prediction", label: "Predict" },
  { to: "/forecasting", label: "Forecast" },
  { to: "/plan-generator", label: "2D Plans" },
  { to: "/visualizer", label: "3D Visualizer" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();
  const { isHoverSpeechEnabled, toggleHoverSpeech, isVoiceNavEnabled, toggleVoiceNav } = useAccessibility();

  return (
    <header className="sticky top-0 z-50 glass">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-3 group transition-transform hover:scale-105">
          <img 
            src={logo} 
            alt="LensEstate Logo" 
            className="h-14 w-auto object-contain drop-shadow-[0_0_15px_rgba(212,175,55,0.4)]" 
          />
          <div className="flex flex-col hidden sm:flex">
            <span className="text-2xl font-extrabold tracking-tight text-white leading-none">
              Lens<span className="gold-text">Estate</span>
            </span>
            <span className="text-[0.6rem] uppercase tracking-[0.2em] text-[oklch(0.7_0.15_220)] font-bold mt-1 glow-cyan-text">
              Smart Investment Solutions
            </span>
          </div>
        </Link>
        <nav className="hidden md:flex items-center gap-7">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              activeProps={{ className: "text-foreground font-medium" }}
              activeOptions={{ exact: l.to === "/" }}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={toggleHoverSpeech}
            className={`flex h-9 w-9 items-center justify-center rounded-xl transition-all ${
              isHoverSpeechEnabled ? "bg-accent text-accent-foreground glow-gold" : "hover:bg-surface/50 text-muted-foreground"
            }`}
            title="Toggle Hover-to-Speech"
          >
            {isHoverSpeechEnabled ? <Volume2 className="h-4.5 w-4.5" /> : <span className="text-lg">🔊</span>}
          </button>
          <button
            onClick={toggleVoiceNav}
            className={`flex h-9 w-9 items-center justify-center rounded-xl transition-all ${
              isVoiceNavEnabled ? "bg-secondary text-white glow-purple" : "hover:bg-surface/50 text-muted-foreground"
            }`}
            title="Toggle Voice Navigation"
          >
            {isVoiceNavEnabled ? <Mic className="h-4.5 w-4.5" /> : <MicOff className="h-4.5 w-4.5" />}
          </button>

          <div className="h-4 w-[1px] bg-border mx-1" />

          {isAuthenticated ? (
            <button
              type="button"
              onClick={logout}
              className="rounded-xl bg-[var(--gradient-primary)] px-4 py-2 text-sm font-medium text-white shadow-md transition-transform hover:scale-105 glow-purple"
            >
              Sign out
            </button>
          ) : (
            <>
              <Link to="/auth" className="text-sm text-muted-foreground hover:text-foreground px-2">
                Sign in
              </Link>
              <Link
                to="/auth"
                className="rounded-xl bg-[var(--gradient-primary)] px-4 py-2 text-sm font-medium text-white shadow-md transition-transform hover:scale-105 glow-purple"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
        <button className="md:hidden text-foreground" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>
    </header>
  );
}
