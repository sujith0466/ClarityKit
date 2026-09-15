import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "./ErrorBoundary";

const ProblematicComponent: React.FC = () => {
  throw new Error("Simulated rendering failure");
};

describe("ErrorBoundary Component", () => {
  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div>Normal content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Normal content")).toBeInTheDocument();
  });

  it("renders default fallback UI when a child throws an error", () => {
    // Suppress console.error in test output for intentional error throw
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ProblematicComponent />
      </ErrorBoundary>
    );

    const alertBox = screen.getByRole("alert");
    expect(alertBox).toBeInTheDocument();
    expect(screen.getByText("Application Error")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it("renders custom fallback UI when provided", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<div>Custom fallback message</div>}>
        <ProblematicComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom fallback message")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
