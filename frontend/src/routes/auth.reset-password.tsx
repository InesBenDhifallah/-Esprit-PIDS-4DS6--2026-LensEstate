import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Lock, ArrowRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { AuthApiError, confirmPasswordReset } from "@/lib/auth";

export const Route = createFileRoute("/auth/reset-password")({
  validateSearch: (search: Record<string, unknown>) => ({
    uid: typeof search.uid === "string" ? search.uid : "",
    token: typeof search.token === "string" ? search.token : "",
  }),
  head: () => ({
    meta: [{ title: "Set new password — LensEstate" }],
  }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const navigate = Route.useNavigate();
  const search = Route.useSearch();
  const { isAuthenticated, isLoading } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void navigate({ to: "/", replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const isValidLink = useMemo(() => Boolean(search.uid && search.token), [search.token, search.uid]);

  const toErrorMessage = (value: unknown): string => {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    if (value && typeof value === "object") {
      const first = Object.values(value as Record<string, unknown>)[0];
      return toErrorMessage(first);
    }
    return "Failed to reset password.";
  };

  const handleSubmit = async () => {
    setError("");

    if (!isValidLink) {
      setError("Invalid reset link");
      return;
    }
    if (!password || !confirmPassword) {
      setError("Please fill in both password fields.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(search.uid, search.token, password);
      await navigate({
        to: "/auth",
        search: { message: "Password reset successful. You can now log in." },
      });
    } catch (submitError) {
      if (submitError instanceof AuthApiError) {
        setError(toErrorMessage(submitError.data) || submitError.message);
      } else {
        setError(submitError instanceof Error ? submitError.message : "Failed to reset password.");
      }
    } finally {
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
        <h1 className="text-2xl font-bold text-center">Create a new password</h1>
        <p className="text-sm text-muted-foreground text-center mt-1">
          Choose a strong password for your LensEstate account.
        </p>

        <div className="mt-7 space-y-4">
          {!isValidLink && <p className="text-xs text-red-400">Invalid reset link</p>}
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface/50 px-4 py-3 focus-within:border-secondary transition">
            <Lock className="h-4 w-4 text-muted-foreground" />
            <input
              type="password"
              placeholder="New password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
          </div>
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface/50 px-4 py-3 focus-within:border-secondary transition">
            <Lock className="h-4 w-4 text-muted-foreground" />
            <input
              type="password"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
          </div>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full rounded-xl bg-[var(--gradient-primary)] py-3 text-sm font-medium text-white inline-flex items-center justify-center gap-2 hover:scale-[1.02] transition glow-purple disabled:opacity-60"
          >
            {loading ? "Please wait..." : "Reset password"} <ArrowRight className="h-4 w-4" />
          </button>
          {error && <p className="text-xs text-red-400">{error}</p>}
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
