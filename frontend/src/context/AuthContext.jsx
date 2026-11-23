/**
 * Who is logged in? Stores the JWT + user in localStorage and exposes login / signup / logout.
 * The backend is the real authority: on start-up we re-check the token with /api/auth/me.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { setUnauthorizedHandler, storage, TOKEN_KEY, USER_KEY } from "../api/client";
import { authApi } from "../api/endpoints";

const AuthContext = createContext(null);

function readStoredUser() {
  try {
    const raw = storage.get(USER_KEY);
    return raw && storage.get(TOKEN_KEY) ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser);
  const [checking, setChecking] = useState(Boolean(storage.get(TOKEN_KEY)));

  const saveSession = (tokenResponse) => {
    storage.set(TOKEN_KEY, tokenResponse.access_token);
    storage.set(USER_KEY, JSON.stringify(tokenResponse.user));
    setUser(tokenResponse.user);
    return tokenResponse.user;
  };

  const logout = useCallback(() => {
    storage.remove(TOKEN_KEY);
    storage.remove(USER_KEY);
    setUser(null);
  }, []);

  // any 401 from the API (expired token) -> log out
  useEffect(() => setUnauthorizedHandler(logout), [logout]);

  // validate a stored token once on start-up
  useEffect(() => {
    if (!storage.get(TOKEN_KEY)) return;
    authApi
      .me()
      .then((me) => {
        storage.set(USER_KEY, JSON.stringify(me));
        setUser(me);
      })
      .catch(() => logout())
      .finally(() => setChecking(false));
  }, [logout]);

  const value = useMemo(
    () => ({
      user,
      checking,
      isStaff: user?.role === "staff",
      login: async (email, password) => saveSession(await authApi.login(email, password)),
      signup: async (payload) => saveSession(await authApi.signup(payload)),
      logout,
    }),
    [user, checking, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export const homeFor = (user) => (user?.role === "staff" ? "/staff/queue" : "/tickets");
