import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("ClarityKit App Shell Smoke Test", () => {
  it("renders the ClarityKit application shell without crashing", () => {
    render(<App />);

    // Verify main banner and header title
    const header = screen.getByRole("banner");
    expect(header).toBeInTheDocument();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: /claritykit/i,
    });
    expect(heading).toBeInTheDocument();

    // Verify product philosophy badge is displayed
    const philosophyBadge = screen.getByLabelText(/product philosophy/i);
    expect(philosophyBadge).toBeInTheDocument();
    expect(philosophyBadge).toHaveTextContent(
      "UNDERSTAND → EXTRACT → EVIDENCE → ASSIST → PREPARE"
    );

    // Verify landmark main and section heading
    const mainSection = screen.getByRole("main");
    expect(mainSection).toBeInTheDocument();

    const foundationHeading = screen.getByRole("heading", {
      level: 2,
      name: /project foundation/i,
    });
    expect(foundationHeading).toBeInTheDocument();

    // Verify placeholder status
    const statusPlaceholder = screen.getByTestId("backend-status-placeholder");
    expect(statusPlaceholder).toBeInTheDocument();
    expect(statusPlaceholder).toHaveTextContent(/backend status:/i);

    // Verify footer contentinfo
    const footer = screen.getByRole("contentinfo");
    expect(footer).toBeInTheDocument();
  });
});
