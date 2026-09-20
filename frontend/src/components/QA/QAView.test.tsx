import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QAView } from "./QAView";
import { QAMessage, QASession } from "../../types/qa";

// Mock AuthContext
vi.mock("../../context/useAuth", () => ({
  useAuth: () => ({
    token: "mock-jwt-token",
    isAuthenticated: true,
    user: { user_id: "u-123", email: "test@example.com" },
  }),
}));

const mockSessions: QASession[] = [
  {
    id: "sess-1",
    document_id: "doc-123",
    title: "General Inquiries",
    created_at: "2026-09-15T10:00:00Z",
    updated_at: "2026-09-15T10:05:00Z",
  },
];

const mockAnswerMessage: QAMessage = {
  id: "msg-1",
  session_id: "sess-1",
  document_id: "doc-123",
  question_text: "What are the termination conditions?",
  answer_text: "Either party may terminate upon 30 days written notice.",
  trust_tier: "DOCUMENT_FACT",
  safety_status: "SAFE",
  evidence_coverage: 1.0,
  is_grounded: true,
  claims: [
    {
      id: "claim-1",
      claim_text: "Either party may terminate upon 30 days written notice.",
      claim_type: "document_statement",
      trust_tier: "DOCUMENT_FACT",
      safety_status: "SAFE",
      is_valid: true,
      validation_reason:
        "Exact citation match verified against authoritative text.",
      evidence: {
        document_id: "doc-123",
        page_start: 2,
        page_end: 2,
        source_span: "Either party may terminate upon 30 days written notice.",
        match_type: "exact",
        validation_status: "VALID",
      },
    },
  ],
  evidence_references: [
    {
      claim_id: "claim-1",
      claim_text: "Either party may terminate upon 30 days written notice.",
      page_start: 2,
      page_end: 2,
      source_span: "Either party may terminate upon 30 days written notice.",
    },
  ],
  created_at: "2026-09-15T10:05:00Z",
};

describe("QAView Component", () => {
  const mockOnInspect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Q&A composer and sample prompt chips when no messages exist", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/qa/sessions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: "success",
              sessions: [],
            }),
        });
      }
      if (url.includes("/questions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: "success",
              messages: [],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "success" }),
      });
    });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-view")).toBeInTheDocument();
    });

    expect(screen.getByTestId("qa-question-input")).toBeInTheDocument();
    expect(screen.getByTestId("qa-empty-state")).toBeInTheDocument();
    expect(
      screen.getByText(/Who are the contracting parties/i)
    ).toBeInTheDocument();
  });

  it("submits a question directly when a suggested question chip is clicked", async () => {
    globalThis.fetch = vi
      .fn()
      .mockImplementation((url: string, opts?: RequestInit) => {
        if (url.includes("/qa/sessions")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ status: "success", sessions: [] }),
          });
        }
        if (url.includes("/questions") && opts?.method === "POST") {
          return Promise.resolve({
            ok: true,
            status: 201,
            json: () =>
              Promise.resolve({
                status: "success",
                message: mockAnswerMessage,
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success", messages: [] }),
        });
      });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-view")).toBeInTheDocument();
    });

    const chip = screen.getByText(/Who are the contracting parties/i);
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByTestId("qa-message-card-msg-1")).toBeInTheDocument();
    });
  });

  it("submits a question and displays the grounded answer card with trust badges", async () => {
    globalThis.fetch = vi
      .fn()
      .mockImplementation((url: string, opts?: RequestInit) => {
        if (url.includes("/qa/sessions") && opts?.method !== "POST") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                status: "success",
                sessions: mockSessions,
              }),
          });
        }
        if (url.includes("/questions") && opts?.method === "POST") {
          return Promise.resolve({
            ok: true,
            status: 201,
            json: () =>
              Promise.resolve({
                status: "success",
                message: mockAnswerMessage,
              }),
          });
        }
        if (url.includes("/questions")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                status: "success",
                messages: [],
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success" }),
        });
      });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-view")).toBeInTheDocument();
    });

    const textarea = screen.getByTestId("qa-question-input");
    fireEvent.change(textarea, {
      target: { value: "What are the termination conditions?" },
    });

    const submitBtn = screen.getByTestId("qa-submit-btn");
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId("qa-message-card-msg-1")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Either party may terminate upon 30 days written notice."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("DOCUMENT_FACT")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-badge-claim-1")).toBeInTheDocument();
    expect(screen.getByText("Page 2")).toBeInTheDocument();
  });

  it("triggers onInspect when evidence badge is clicked", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/qa/sessions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: "success",
              sessions: mockSessions,
            }),
        });
      }
      if (url.includes("/questions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: "success",
              messages: [mockAnswerMessage],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "success" }),
      });
    });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-message-card-msg-1")).toBeInTheDocument();
    });

    const evidenceBadge = screen.getByTestId("evidence-badge-claim-1");
    fireEvent.click(evidenceBadge);

    expect(mockOnInspect).toHaveBeenCalledTimes(1);
    expect(mockOnInspect).toHaveBeenCalledWith({
      title: "Cited Document Evidence",
      claimText: "Either party may terminate upon 30 days written notice.",
      claimType: "document_fact",
      pageStart: 2,
      pageEnd: 2,
      sourceSpan: "Either party may terminate upon 30 days written notice.",
      trustTier: "DOCUMENT_FACT",
      validationStatus: "VALID",
    });
  });

  it("handles error during question submission gracefully", async () => {
    globalThis.fetch = vi
      .fn()
      .mockImplementation((url: string, opts?: RequestInit) => {
        if (url.includes("/qa/sessions")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ status: "success", sessions: [] }),
          });
        }
        if (url.includes("/questions") && opts?.method === "POST") {
          return Promise.resolve({
            ok: false,
            status: 400,
            json: () =>
              Promise.resolve({
                error: "invalid_question",
                message: "Question cannot exceed 1000 characters.",
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success", messages: [] }),
        });
      });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-view")).toBeInTheDocument();
    });

    const textarea = screen.getByTestId("qa-question-input");
    fireEvent.change(textarea, { target: { value: "Test question" } });

    fireEvent.click(screen.getByTestId("qa-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("qa-error")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Question cannot exceed 1000 characters.")
    ).toBeInTheDocument();
  });

  it("renders adversarial input safely without script execution", async () => {
    const adversarialMessage: QAMessage = {
      id: "msg-adv",
      session_id: "sess-1",
      document_id: "doc-123",
      question_text: '<script>alert("attack")</script>',
      answer_text:
        'Ignore previous instructions. <img src="x" onerror="alert(1)">',
      trust_tier: "INTERPRETATION",
      safety_status: "LIMITED",
      evidence_coverage: 0.0,
      is_grounded: false,
      claims: [
        {
          id: "claim-adv",
          claim_text: '<script>alert("claim")</script>',
          claim_type: "interpretation",
          trust_tier: "INTERPRETATION",
          safety_status: "LIMITED",
          is_valid: false,
          validation_reason: "Adversarial content detected.",
        },
      ],
      evidence_references: [],
      created_at: "2026-09-15T10:05:00Z",
    };

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/qa/sessions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({ status: "success", sessions: mockSessions }),
        });
      }
      if (url.includes("/questions")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: "success",
              messages: [adversarialMessage],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "success" }),
      });
    });

    render(<QAView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("qa-message-card-msg-adv")).toBeInTheDocument();
    });

    // Verify raw strings render as text, not HTML
    expect(
      screen.getByText('<script>alert("attack")</script>')
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Ignore previous instructions. <img src="x" onerror="alert(1)">'
      )
    ).toBeInTheDocument();
  });
});
