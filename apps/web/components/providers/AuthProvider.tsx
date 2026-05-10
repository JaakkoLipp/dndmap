"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  type ReactNode
} from "react";

import { api, ApiError, queryKeys, type User } from "../../lib/api";

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const meQuery = useQuery({
    queryKey: queryKeys.authMe,
    queryFn: async () => {
      try {
        return await api.auth.me();
      } catch (error) {
        if (
          error instanceof ApiError &&
          (error.status === 401 || error.status === 503)
        ) {
          return null;
        }
        throw error;
      }
    },
    retry: false
  });

  const logoutMutation = useMutation({
    mutationFn: api.auth.logout,
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.authMe });
    }
  });

  return (
    <AuthContext.Provider
      value={{
        user: meQuery.data ?? null,
        isLoading: meQuery.isLoading,
        isAuthenticated: Boolean(meQuery.data),
        logout: async () => {
          await logoutMutation.mutateAsync();
        }
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
