import React, { useState } from "react";
import { useAuth } from "../../context/useAuth";

interface RegisterFormProps {
  onSuccess?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const { login, setError, error } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          password,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.message || "Registration failed.");
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
      aria-labelledby="register-heading"
    >
      <h2 id="register-heading">Create ClarityKit Account</h2>

      {error && (
        <div
          id="register-error-banner"
          className="auth-error-banner"
          role="alert"
          aria-live="assertive"
          data-testid="auth-error-banner"
        >
          {error}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="register-name">Full Name</label>
        <input
          id="register-name"
          type="text"
          name="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          autoComplete="name"
          disabled={isSubmitting}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "register-error-banner" : undefined}
        />
      </div>

      <div className="form-group">
        <label htmlFor="register-email">Email Address</label>
        <input
          id="register-email"
          type="email"
          name="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          disabled={isSubmitting}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "register-error-banner" : undefined}
        />
      </div>

      <div className="form-group">
        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          name="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={isSubmitting}
          aria-invalid={Boolean(error)}
          aria-describedby={
            error
              ? "register-error-banner register-pwd-hint"
              : "register-pwd-hint"
          }
        />
        <small id="register-pwd-hint" className="form-hint">
          Must be at least 8 characters with letters and numbers.
        </small>
      </div>

      <button
        type="submit"
        className="btn-primary"
        disabled={isSubmitting}
        aria-busy={isSubmitting}
      >
        {isSubmitting ? "Creating Account..." : "Create Account"}
      </button>
    </form>
  );
};
