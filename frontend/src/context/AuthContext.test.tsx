import React from "react";
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "./useAuth";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe("AuthContext", () => {
  it("initializes with unauthenticated state", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it("updates state on login and clears state on logout", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const mockUser = {
      user_id: "u-123",
      email: "user@example.com",
      name: "Test User",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    act(() => {
      result.current.login("user@example.com", "token-xyz", mockUser);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe("token-xyz");
    expect(result.current.user?.email).toBe("user@example.com");

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });
});
