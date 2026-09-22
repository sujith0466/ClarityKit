import React, { useState } from "react";
import { useAuth } from "../../context/useAuth";

interface LoginFormProps {
  onSuccess?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const { login, setError, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.message || "Failed to login.");
        setIsSubmitting(false);
        return;
      }

      login(data.user.email, data.token, data.user);
      if (onSuccess) {
        onSuccess();
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      className="auth-form"
      onSubmit={handleSubmit}
      noValidate
      aria-labelledby="login-heading"
    >
      <h2 id="login-heading">Sign In to ClarityKit</h2>

      {error && (
        <div
          id="login-error-banner"
          className="auth-error-banner"
          role="alert"
          aria-live="assertive"
          data-testid="auth-error-banner"
        >
          {error}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="login-email">Email Address</label>
        <input
          id="login-email"
          type="email"
          name="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          disabled={isSubmitting}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "login-error-banner" : undefined}
        />
      </div>

      <div className="form-group">
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          name="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          disabled={isSubmitting}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "login-error-banner" : undefined}
        />
      </div>

      <button
        type="submit"
        className="btn-primary"
        disabled={isSubmitting}
        aria-busy={isSubmitting}
      >
        {isSubmitting ? "Signing in..." : "Sign In"}
      </button>
    </form>
  );
};
