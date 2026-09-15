import React from "react";
import { MainLayout } from "./components/Shell/MainLayout";
import { ErrorBoundary } from "./components/ErrorBoundary/ErrorBoundary";
import "./App.css";

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <MainLayout>
        <section className="card" aria-labelledby="foundation-heading">
          <h2 id="foundation-heading">Project Foundation (Phase 1)</h2>
          <p>
            The engineering scaffold, quality tooling, and test frameworks are
            initialized. Intelligence layers and workspace modules will be
            incrementally integrated following the Master Plan.
          </p>

          {/* Placeholder status indicator - no active backend polling in Phase 1 shell */}
          <div
            className="status-placeholder"
            data-testid="backend-status-placeholder"
          >
            <span className="status-dot" aria-hidden="true" />
            <span>Backend status: Ready for integration</span>
          </div>
        </section>
      </MainLayout>
    </ErrorBoundary>
  );
};

export default App;
