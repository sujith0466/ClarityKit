/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useState, type ReactNode } from "react";
import type { AuthState, AuthUser } from "../types/auth";

export interface AuthContextType extends AuthState {
  login: (email: string, token: string, user: AuthUser) => void;
  logout: () => void;
  setError: (error: string | null) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading] = useState<boolean>(false);

  const login = (_email: string, newToken: string, newUser: AuthUser) => {
    setToken(newToken);
    setUser(newUser);
    setError(null);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setError(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        error,
        login,
        logout,
        setError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
