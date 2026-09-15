import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

    const securityHeading = screen.getByRole("heading", {
      level: 2,
      name: /security & authentication/i,
    });
    expect(securityHeading).toBeInTheDocument();

    // Verify placeholder status
    const statusPlaceholder = screen.getByTestId("backend-status-placeholder");
    expect(statusPlaceholder).toBeInTheDocument();
    expect(statusPlaceholder).toHaveTextContent(/security boundary:/i);

    // Verify footer contentinfo
    const footer = screen.getByRole("contentinfo");
    expect(footer).toBeInTheDocument();

    // Verify login form is default
    expect(
      screen.getByRole("heading", { name: /sign in to claritykit/i })
    ).toBeInTheDocument();
  });

  it("toggles between sign in and create account forms", () => {
    render(<App />);

    // Click Create Account button
    const createAccountBtn = screen.getByRole("button", {
      name: /create account/i,
    });
    fireEvent.click(createAccountBtn);

    expect(
      screen.getByRole("heading", { name: /create claritykit account/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();

    // Click Sign In button
    const signInBtn = screen.getByRole("button", { name: /sign in/i });
    fireEvent.click(signInBtn);

    expect(
      screen.getByRole("heading", { name: /sign in to claritykit/i })
    ).toBeInTheDocument();
  });
});
