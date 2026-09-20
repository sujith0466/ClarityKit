import React, { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../../context/useAuth";
import { config } from "../../config";
import { QAMessage, QASession } from "../../types/qa";
import { InspectionTarget } from "../../types/workspace";
import { AnswerCard } from "./AnswerCard";
import { QuestionComposer } from "./QuestionComposer";

interface QAViewProps {
  readonly documentId: string;
  readonly documentFilename?: string;
  readonly onInspect: (target: InspectionTarget) => void;
}

export const QAView: React.FC<QAViewProps> = ({
  documentId,
  documentFilename = "this document",
  onInspect,
}) => {
  const { token } = useAuth();
  const [messages, setMessages] = useState<readonly QAMessage[]>([]);
  const [activeSession, setActiveSession] = useState<QASession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const fetchHistory = useCallback(async () => {
    if (!token || !documentId) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch sessions
      const sessRes = await fetch(
        `${config.apiBaseUrl}/api/documents/${documentId}/qa/sessions`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (sessRes.ok) {
        const sessData = await sessRes.json();
        const sessions: QASession[] = sessData.sessions || [];
        if (sessions.length > 0) {
          setActiveSession(sessions[0]);
        }
      }

      // 2. Fetch messages
      const res = await fetch(
        `${config.apiBaseUrl}/api/documents/${documentId}/questions`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.message || "Failed to load Q&A history.");
      }
    } catch {
      setError("Network error while connecting to Q&A service.");
    } finally {
      setIsLoading(false);
    }
  }, [token, documentId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleAskQuestion = async (questionText: string) => {
    if (!token || !documentId) return;
    setIsAsking(true);
    setError(null);

    try {
      const res = await fetch(
        `${config.apiBaseUrl}/api/documents/${documentId}/questions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            question: questionText,
            session_id: activeSession?.id,
          }),
        }
      );

      if (res.ok) {
        const data = await res.json();
        if (data.message) {
          setMessages((prev) => [...prev, data.message]);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.message || "Failed to generate answer.");
      }
    } catch {
      setError("Network error while communicating with Q&A service.");
    } finally {
      setIsAsking(false);
    }
  };

  const handleCreateNewSession = async () => {
    if (!token || !documentId) return;
    setIsLoading(true);
    try {
      const res = await fetch(
        `${config.apiBaseUrl}/api/documents/${documentId}/qa/sessions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title: `Session ${new Date().toLocaleTimeString()}`,
          }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setActiveSession(data.session);
        setMessages([]);
      }
    } catch {
      setError("Failed to create new session.");
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    "Who are the contracting parties?",
    "How can either party terminate this agreement?",
    "What are the payment and fee terms?",
    "What are the confidentiality obligations?",
    "What is the governing law?",
  ];

  return (
    <div className="qa-view-container" data-testid="qa-view">
      {/* QA Header */}
      <div className="qa-header-row">
        <div>
          <h2 className="qa-view-title">Grounded Document Q&amp;A</h2>
          <p className="qa-view-desc">
            Ask questions about <strong>{documentFilename}</strong>. Every
            answer is grounded in authoritative page text with verifiable
            evidence.
          </p>
        </div>
        <div className="qa-actions">
          <button
            type="button"
            className="btn-secondary-sm"
            onClick={handleCreateNewSession}
            disabled={isLoading || isAsking}
            data-testid="qa-new-session-btn"
          >
            + New Thread
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-banner error" role="alert" data-testid="qa-error">
          {error}
        </div>
      )}

      {/* Messages Thread Container */}
      <div className="qa-thread-container" data-testid="qa-messages-list">
        {isLoading && messages.length === 0 ? (
          <div className="qa-loading-state" data-testid="qa-loading">
            <div className="spinner" />
            <p>Loading Q&amp;A history...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="qa-empty-state" data-testid="qa-empty-state">
            <div className="empty-icon" aria-hidden="true">
              &#128172;
            </div>
            <h3 className="empty-title">Ask Anything About This Document</h3>
            <p className="empty-desc">
              Select a suggested question below or enter your own query:
            </p>
            <div className="sample-prompts-grid">
              {sampleQuestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="sample-prompt-chip"
                  onClick={() => handleAskQuestion(q)}
                  disabled={isAsking}
                  data-testid={`sample-prompt-${q.slice(0, 10).toLowerCase().replace(/\s+/g, "-")}`}
                >
                  &ldquo;{q}&rdquo;
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="qa-messages-flow">
            {messages.map((msg) => (
              <AnswerCard key={msg.id} message={msg} onInspect={onInspect} />
            ))}
            {isAsking && (
              <div className="qa-thinking-indicator" data-testid="qa-thinking">
                <div className="spinner-sm" />
                <span>
                  Searching document chunks and validating evidence...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Fixed Question Composer */}
      <div className="qa-composer-container">
        <QuestionComposer
          onSubmit={handleAskQuestion}
          isLoading={isAsking}
          disabled={isLoading}
        />
      </div>
    </div>
  );
};
