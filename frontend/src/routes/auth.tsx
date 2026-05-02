import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Sparkles, Mail, Lock, User, ArrowRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useGoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";
import { AuthApiError } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  validateSearch: (search: Record<string, unknown>) => ({
    verified: search.verified === "true",
    message: typeof search.message === "string" ? search.message : "",
    uid:
      typeof search.uid === "string"
        ? search.uid
        : typeof search.uid === "number"
          ? String(search.uid)
          : typeof search.uidb64 === "string"
            ? search.uidb64
            : "",
    token:
      typeof search.token === "string"
        ? search.token
        : typeof search.token === "number"
          ? String(search.token)
          : "",
    uidb64: typeof search.uidb64 === "string" ? search.uidb64 : "",
  }),
  head: () => ({
    meta: [
      { title: "Sign in — LensEstate" },
      { name: "description", content: "Sign in or create your LensEstate account." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = Route.useNavigate();
  const search = Route.useSearch();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { login, loginWithGoogle, register, isAuthenticated, isLoading } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [registerSuccess, setRegisterSuccess] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void navigate({ to: "/", replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const infoBanner = useMemo(() => {
    if (search.verified) return "Email verified! You can now log in.";
    if (search.message) return search.message;
    return "";
  }, [search.message, search.verified]);

  const googleSignIn = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setError("");
      setLoading(true);
      try {
        await loginWithGoogle(tokenResponse.access_token);
      } catch (googleError) {
        setError(googleError instanceof Error ? googleError.message : "Google sign-in failed.");
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setError("Google sign-in failed.");
    },
  });

  const mapLoginError = (rawMessage: string): string => {
    if (rawMessage === "Invalid credentials") return "Invalid username or password";
    if (rawMessage === "Please verify your email before logging in") {
      return "Please verify your email first. Check your inbox.";
    }
    if (rawMessage === "Account locked due to too many failed attempts") {
      return "Account locked. Try again in 1 hour.";
    }
    return rawMessage;
  };

  const handleSubmit = async () => {
    setError("");
    setRegisterSuccess("");
    setFieldErrors({});
    setLoading(true);
    try {
      if (mode === "signin") {
        await login(username, password);
        return;
      } else {
        await register(username, email, password, phone);
        setRegisterSuccess(
          `Account created! We sent a verification email to ${email}. Please check your inbox and click the link before logging in.`,
        );
        setMode("signin");
        setPassword("");
        return;
      }
    } catch (submitError) {
      if (submitError instanceof AuthApiError) {
        if (mode === "signup" && submitError.data && typeof submitError.data === "object") {
          const raw = submitError.data as Record<string, unknown>;
          const nextErrors: Record<string, string> = {};
          if (Array.isArray(raw.username) && typeof raw.username[0] === "string") {
            nextErrors.username = raw.username[0];
          }
          if (Array.isArray(raw.email) && typeof raw.email[0] === "string") {
            nextErrors.email = raw.email[0];
          }
          if (Array.isArray(raw.password) && typeof raw.password[0] === "string") {
            nextErrors.password = raw.password[0];
          }
          setFieldErrors(nextErrors);
        }
        setError(mode === "signin" ? mapLoginError(submitError.message) : submitError.message);
      } else {
        setError(submitError instanceof Error ? submitError.message : "Authentication failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (pathname !== "/auth") {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute inset-0 -z-10" style={{ background: "var(--gradient-hero)" }} />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md rounded-3xl glass p-8 shadow-2xl"
      >
        <Link to="/" className="flex items-center gap-2 justify-center mb-6">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gradient-primary)] glow-purple">
            <Sparkles className="h-5 w-5 text-white" />
          </span>
          <span className="font-semibold text-lg">
            Lens<span className="gold-text">Estate</span>
          </span>
        </Link>
        <h1 className="text-2xl font-bold text-center">
          {mode === "signin" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="text-sm text-muted-foreground text-center mt-1">
          {mode === "signin"
            ? "Sign in to continue your search"
            : "Start exploring AI-driven real estate"}
        </p>

        <div className="mt-7 space-y-4">
          {infoBanner && (
            <p className="rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-300">
              {infoBanner}
            </p>
          )}
          {registerSuccess && (
            <p className="rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-300">
              {registerSuccess}
            </p>
          )}
          {mode === "signup" && (
            <>
              <Field
                icon={User}
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                error={fieldErrors.username}
              />
              <Field
                icon={Mail}
                placeholder="Email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={fieldErrors.email}
              />
              <Field
                icon={User}
                placeholder="Phone number"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </>
          )}
          {mode === "signin" && (
            <Field
              icon={User}
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          )}
          <Field
            icon={Lock}
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={mode === "signup" ? fieldErrors.password : ""}
          />
          {mode === "signin" && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => void navigate({ to: "/auth/forgot-password" })}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Forgot password?
              </button>
            </div>
          )}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full rounded-xl bg-[var(--gradient-primary)] py-3 text-sm font-medium text-white inline-flex items-center justify-center gap-2 hover:scale-[1.02] transition glow-purple disabled:opacity-60"
          >
            {loading ? "Please wait..." : mode === "signin" ? "Sign in" : "Create account"}{" "}
            <ArrowRight className="h-4 w-4" />
          </button>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>

        <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
          <div className="h-px flex-1 bg-border" /> or continue with{" "}
          <div className="h-px flex-1 bg-border" />
        </div>

        <div className="grid grid-cols-1 gap-3">
          <button
            type="button"
            onClick={() => googleSignIn()}
            disabled={loading}
            className="rounded-xl border border-border bg-surface/50 py-2.5 text-sm hover:border-secondary transition disabled:opacity-60"
          >
            Continue with Google
          </button>
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          {mode === "signin" ? "New here?" : "Already have an account?"}{" "}
          <button
            onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
            className="gold-text font-medium"
          >
            {mode === "signin" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </motion.div>
    </div>
  );
}

function Field({
  icon: Icon,
  error,
  ...props
}: { icon: typeof Mail; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <div
        className={`flex items-center gap-3 rounded-xl border bg-surface/50 px-4 py-3 transition ${error ? "border-red-400/60" : "border-border focus-within:border-secondary"}`}
      >
        <Icon className="h-4 w-4 text-muted-foreground" />
        <input
          {...props}
          className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
        />
      </div>
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}
