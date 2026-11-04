import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, login as apiLogin, setAuthLostHandler, tokens } from '../api/client';

const AuthContext = createContext(null);
export const FIRM_ROLES = ['admin', 'staff', 'lawyer'];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setAuthLostHandler(() => setUser(null));
    if (!tokens.access && !tokens.refresh) { setReady(true); return; }
    api.get('/api/auth/me/')
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setReady(true));
  }, []);

  const value = useMemo(() => ({
    user,
    ready,
    isFirm: !!user && FIRM_ROLES.includes(user.role),
    isClient: user?.role === 'client',
    isAdmin: user?.role === 'admin',
    hasRole: (...roles) => !!user && roles.includes(user.role),
    async login(username, password) {
      const me = await apiLogin(username, password);
      setUser(me);
      return me;
    },
    logout,
  }), [user, ready, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
