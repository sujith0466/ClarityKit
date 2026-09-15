import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "../../context/AuthContext";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

describe("Authentication Forms", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("LoginForm", () => {
    it("renders accessible login form with labels and controls", () => {
      render(
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      );

      expect(
        screen.getByRole("heading", { name: /sign in/i })
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /sign in/i })
      ).toBeInTheDocument();
    });

    it("displays error when submitting empty fields", async () => {
      render(
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      );

      fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(
          screen.getByText(/please fill in all required fields/i)
        ).toBeInTheDocument();
      });
    });

    it("handles successful login response", async () => {
      const onSuccess = vi.fn();
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          status: "success",
          token: "mock-jwt-token",
          user: {
            user_id: "u-1",
            email: "test@example.com",
            name: "Test User",
            is_active: true,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        }),
      } as unknown as Response);

      render(
        <AuthProvider>
          <LoginForm onSuccess={onSuccess} />
        </AuthProvider>
      );

      fireEvent.change(screen.getByLabelText(/email address/i), {
        target: { value: "test@example.com" },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: "Password123" },
      });
      fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("RegisterForm", () => {
    it("renders accessible registration form with labels and hints", () => {
      render(
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      );

      expect(
        screen.getByRole("heading", { name: /create claritykit account/i })
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /create account/i })
      ).toBeInTheDocument();
    });

    it("displays validation error when password is too short", async () => {
      render(
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      );

      fireEvent.change(screen.getByLabelText(/full name/i), {
        target: { value: "John Doe" },
      });
      fireEvent.change(screen.getByLabelText(/email address/i), {
        target: { value: "john@example.com" },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: "short" },
      });
      fireEvent.click(screen.getByRole("button", { name: /create account/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(
          screen.getByText(/password must be at least 8 characters/i)
        ).toBeInTheDocument();
      });
    });
  });
});
