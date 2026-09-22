import React, { useState } from "react";
import { MainLayout } from "./components/Shell/MainLayout";
import { ErrorBoundary } from "./components/ErrorBoundary/ErrorBoundary";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import { LoginForm } from "./components/Auth/LoginForm";
import { RegisterForm } from "./components/Auth/RegisterForm";
import { DocumentsManager } from "./components/Documents/DocumentsManager";
import { ComparisonWorkspace } from "./components/Comparison/ComparisonWorkspace";
import { VersionDiffWorkspace } from "./components/VersionDiff/VersionDiffWorkspace";
import { TimelineWorkspace } from "./components/Timeline/TimelineWorkspace";
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
  const { isAuthenticated } = useAuth();
  const [activeNav, setActiveNav] = useState<
    "documents" | "comparison" | "version-diff" | "timeline"
  >("documents");

  return (
    <ErrorBoundary>
      <MainLayout>
        <section className="card" aria-labelledby="foundation-heading">
          <h2 id="foundation-heading">Secure Document Ingestion (Phase 3)</h2>
          <p>
            Secure intake, strict PDF signature validation, namespaced storage,
            and tenant-isolated document management are established.
          </p>

          <div
            className="status-placeholder"
            data-testid="backend-status-placeholder"
          >
            <span className="status-dot" aria-hidden="true" />
            <span>Document Ingestion: Active &amp; Protected</span>
          </div>
        </section>

        <AuthSection />

        {isAuthenticated && (
          <nav
            className="workspace-main-nav"
            aria-label="Main Application Navigation"
          >
            <button
              type="button"
              className={`nav-tab-btn ${activeNav === "documents" ? "active" : ""}`}
              onClick={() => setActiveNav("documents")}
              aria-current={activeNav === "documents" ? "page" : undefined}
            >
              📄 Documents &amp; Workspace
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeNav === "comparison" ? "active" : ""}`}
              onClick={() => setActiveNav("comparison")}
              aria-current={activeNav === "comparison" ? "page" : undefined}
            >
              ⚖️ Multi-Document Comparison
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeNav === "version-diff" ? "active" : ""}`}
              onClick={() => setActiveNav("version-diff")}
              aria-current={activeNav === "version-diff" ? "page" : undefined}
            >
              🔀 Document Version Diff
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeNav === "timeline" ? "active" : ""}`}
              onClick={() => setActiveNav("timeline")}
              aria-current={activeNav === "timeline" ? "page" : undefined}
            >
              ⏱️ Deadline &amp; Timeline
            </button>
          </nav>
        )}

        {isAuthenticated && activeNav === "comparison" && (
          <ComparisonWorkspace />
        )}
        {isAuthenticated && activeNav === "version-diff" && (
          <VersionDiffWorkspace />
        )}
        {isAuthenticated && activeNav === "timeline" && <TimelineWorkspace />}
        {isAuthenticated && activeNav === "documents" && <DocumentsManager />}
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
