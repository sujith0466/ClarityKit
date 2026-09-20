import React, { useState } from "react";

interface QuestionComposerProps {
  readonly onSubmit: (question: string) => Promise<void>;
  readonly isLoading: boolean;
  readonly disabled?: boolean;
}

const MAX_QUESTION_CHARS = 2000;

export const QuestionComposer: React.FC<QuestionComposerProps> = ({
  onSubmit,
  isLoading,
  disabled = false,
}) => {
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = question.trim();
    if (!clean) {
      setError("Please enter a question.");
      return;
    }
    if (clean.length > MAX_QUESTION_CHARS) {
      setError(`Question exceeds limit of ${MAX_QUESTION_CHARS} characters.`);
      return;
    }

    setError(null);
    try {
      await onSubmit(clean);
      setQuestion("");
    } catch {
      // Error handled by parent
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      void handleSubmit(e);
    }
  };

  return (
    <form
      className="qa-composer-form"
      onSubmit={handleSubmit}
      data-testid="qa-question-composer"
    >
      <div className="composer-input-wrapper">
        <label htmlFor="qa-question-input" className="sr-only">
          Ask a question about this document
        </label>
        <textarea
          id="qa-question-input"
          className="qa-textarea"
          value={question}
          onChange={(e) => {
            setQuestion(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about this document (e.g. 'What is the governing law?' or 'How can either party terminate?')..."
          rows={3}
          maxLength={MAX_QUESTION_CHARS}
          disabled={isLoading || disabled}
          aria-describedby="char-count"
          data-testid="qa-question-input"
        />
        <div className="composer-bottom-bar">
          <span id="char-count" className="char-counter">
            {question.length} / {MAX_QUESTION_CHARS}
          </span>
          <button
            type="submit"
            className="btn-primary qa-submit-btn"
            disabled={isLoading || disabled || !question.trim()}
            data-testid="qa-submit-btn"
          >
            {isLoading ? "Analyzing..." : "Ask Question"}
          </button>
        </div>
      </div>
      {error && (
        <div
          className="composer-error-text"
          role="alert"
          data-testid="composer-error"
        >
          {error}
        </div>
      )}
    </form>
  );
};
