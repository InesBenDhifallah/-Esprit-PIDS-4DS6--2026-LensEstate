import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Mail, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { requestPasswordReset } from "@/lib/auth";

export const Route = createFileRoute("/auth/forgot-password")({
  head: () => ({
    meta: [{ title: "Forgot password — LensEstate" }],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const navigate = Route.useNavigate();
  const { isAuthenticated, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void navigate({ to: "/", replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await requestPasswordReset(email);
    } catch {
      // Intentionally hidden to avoid email enumeration.
    } finally {
      setMessage("If this email is registered, you'll receive a reset link shortly.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute inset-0 -z-10" style={{ background: "var(--gradient-hero)" }} />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md rounded-3xl glass p-8 shadow-2xl"
      >
        <h1 className="text-2xl font-bold text-center">Reset your password</h1>
        <p className="text-sm text-muted-foreground text-center mt-1">
          Enter your email and we'll send you a reset link.
        </p>

        <div className="mt-7 space-y-4">
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface/50 px-4 py-3 focus-within:border-secondary transition">
            <Mail className="h-4 w-4 text-muted-foreground" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
          </div>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full rounded-xl bg-[var(--gradient-primary)] py-3 text-sm font-medium text-white inline-flex items-center justify-center gap-2 hover:scale-[1.02] transition glow-purple disabled:opacity-60"
          >
            {loading ? "Please wait..." : "Send reset link"} <ArrowRight className="h-4 w-4" />
          </button>
          {message && <p className="text-xs text-emerald-300">{message}</p>}
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link to="/auth" className="gold-text font-medium">
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
