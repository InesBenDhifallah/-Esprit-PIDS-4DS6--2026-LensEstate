import { Link } from "@tanstack/react-router";
import { Sparkles, Menu, X } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

const links = [
  { to: "/", label: "Home" },
  { to: "/map", label: "Explore" },
  { to: "/ai-chat", label: "AI Chat" },
  { to: "/price-prediction", label: "Predict" },
  { to: "/forecasting", label: "Forecast" },
  { to: "/plan-generator", label: "2D Plans" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();
  return (
    <header className="sticky top-0 z-50 glass">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2 group">
          <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--gradient-primary)] glow-purple">
            <Sparkles className="h-5 w-5 text-white" />
          </span>
          <span className="text-lg font-semibold tracking-tight">
            Lens<span className="gold-text">Estate</span>
          </span>
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
              <Link to="/auth" className="text-sm text-muted-foreground hover:text-foreground">
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
      {open && (
        <div className="md:hidden border-t border-border px-6 py-4 space-y-3 glass">
          {links.map((l) => (
            <Link key={l.to} to={l.to} className="block text-sm" onClick={() => setOpen(false)}>
              {l.label}
            </Link>
          ))}
          {isAuthenticated ? (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                logout();
              }}
              className="block text-sm gold-text"
            >
              Sign out
            </button>
          ) : (
            <Link to="/auth" className="block text-sm gold-text" onClick={() => setOpen(false)}>
              Sign in / Get started
            </Link>
          )}
        </div>
      )}
    </header>
  );
}
