import React, { useState } from "react";
import { MainLayout } from "./components/Shell/MainLayout";
import { ErrorBoundary } from "./components/ErrorBoundary/ErrorBoundary";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import { LoginForm } from "./components/Auth/LoginForm";
import { RegisterForm } from "./components/Auth/RegisterForm";
import "./App.css";

const AuthSection: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  if (isAuthenticated && user) {
    return (
      <section className="card" aria-labelledby="auth-profile-heading">
        <h2 id="auth-profile-heading">Authenticated Identity</h2>
        <p>
          Logged in as <strong>{user.name}</strong> ({user.email})
        </p>
        <div style={{ marginTop: "1rem" }}>
          <button type="button" className="btn-primary" onClick={logout}>
            Sign Out
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card" aria-labelledby="auth-portal-heading">
      <h2 id="auth-portal-heading" className="sr-only">
        Authentication
      </h2>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          className="btn-primary"
          style={{
            backgroundColor: authMode === "login" ? "#0284c7" : "#e2e8f0",
            color: authMode === "login" ? "#ffffff" : "#334155",
          }}
          onClick={() => setAuthMode("login")}
        >
          Sign In
        </button>
        <button
          type="button"
          className="btn-primary"
          style={{
            backgroundColor: authMode === "register" ? "#0284c7" : "#e2e8f0",
            color: authMode === "register" ? "#ffffff" : "#334155",
          }}
          onClick={() => setAuthMode("register")}
        >
          Create Account
        </button>
      </div>

      {authMode === "login" ? <LoginForm /> : <RegisterForm />}
    </section>
  );
};

export const AppContent: React.FC = () => {
  return (
    <ErrorBoundary>
      <MainLayout>
        <section className="card" aria-labelledby="foundation-heading">
          <h2 id="foundation-heading">Security & Authentication (Phase 2)</h2>
          <p>
            Authentication, authorization, and tenant isolation boundaries are
            established. All resources enforce strict server-side ownership and
            IDOR protection.
          </p>

          <div
            className="status-placeholder"
            data-testid="backend-status-placeholder"
          >
            <span className="status-dot" aria-hidden="true" />
            <span>Security boundary: Active & Protected</span>
          </div>
        </section>

        <AuthSection />
      </MainLayout>
    </ErrorBoundary>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
