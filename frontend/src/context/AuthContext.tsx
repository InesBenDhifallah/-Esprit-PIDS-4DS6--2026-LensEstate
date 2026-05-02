import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { apiRequest } from "@/lib/api";
import * as authApi from "@/lib/auth";
import type { User } from "@/types/user";

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginWithGoogle: (accessToken: string) => Promise<void>;
  register: (username: string, email: string, password: string, phone: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const me = await apiRequest<User>("/api/users/me/");
    setUser(me);
  }, []);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      await authApi.login(username, password);
      await refreshUser();
      await router.navigate({ to: "/" });
    },
    [refreshUser, router],
  );

  const handleGoogleLogin = useCallback(
    async (accessToken: string) => {
      await authApi.loginWithGoogle(accessToken);
      await refreshUser();
      await router.navigate({ to: "/" });
    },
    [refreshUser, router],
  );

  const handleRegister = useCallback(
    async (username: string, email: string, password: string, phone: string) => {
      await authApi.register(username, email, password, phone);
    },
    [],
  );

  const handleLogout = useCallback(() => {
    void authApi.logoutRemote();
    authApi.logout();
    setUser(null);
    void router.navigate({ to: "/auth" });
  }, [router]);

  useEffect(() => {
    const restoreSession = async () => {
      const token = authApi.getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        if (authApi.isTokenExpired(token)) {
          const refreshed = await authApi.refreshToken();
          if (!refreshed) {
            authApi.logout();
            setUser(null);
            setIsLoading(false);
            return;
          }
        }
        await refreshUser();
      } catch {
        authApi.logout();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, [refreshUser]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login: handleLogin,
      loginWithGoogle: handleGoogleLogin,
      register: handleRegister,
      logout: handleLogout,
      refreshUser,
    }),
    [user, isLoading, handleLogin, handleGoogleLogin, handleRegister, handleLogout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
