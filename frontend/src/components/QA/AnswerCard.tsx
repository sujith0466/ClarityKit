import React from "react";
import { QAMessage } from "../../types/qa";
import { InspectionTarget } from "../../types/workspace";
import { EvidenceBadge } from "./EvidenceBadge";
import { QASafetyNotice } from "./QASafetyNotice";

interface AnswerCardProps {
  readonly message: QAMessage;
  readonly onInspect: (target: InspectionTarget) => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  message,
  onInspect,
}) => {
  const coveragePercent = Math.round(message.evidence_coverage * 100);

  const getTierBadgeClass = (tier: string) => {
    switch (tier) {
      case "DOCUMENT_FACT":
        return "badge-tier fact";
      case "INTERPRETATION":
        return "badge-tier interpretation";
      case "PROFESSIONAL_REVIEW_NEEDED":
        return "badge-tier review";
      default:
        return "badge-tier";
    }
  };

  const getSafetyBadgeClass = (status: string) => {
    switch (status) {
      case "SAFE":
        return "badge-status-safe";
      case "LIMITED":
        return "badge-status-limited";
      case "REVIEW_REQUIRED":
        return "badge-status-review";
      case "UNSUPPORTED":
        return "badge-status-unsupported";
      default:
        return "badge-status-safe";
    }
  };

  return (
    <article
      className="qa-message-card"
      data-testid={`qa-message-card-${message.id}`}
      aria-labelledby={`question-title-${message.id}`}
    >
      {/* User Question */}
      <div className="qa-user-question-row">
        <span className="user-icon" aria-hidden="true">
          &#128100;
        </span>
        <div className="question-content">
          <h3 id={`question-title-${message.id}`} className="question-text">
            {message.question_text}
          </h3>
          <time className="message-timestamp">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>
      </div>

      {/* Assistant Grounded Answer */}
      <div className="qa-assistant-answer-row">
        <div className="assistant-avatar" aria-hidden="true">
          CK
        </div>
        <div className="answer-content">
          <div className="answer-header-badges">
            <span className={getTierBadgeClass(message.trust_tier)}>
              {message.trust_tier}
            </span>
            <span className={getSafetyBadgeClass(message.safety_status)}>
              {message.safety_status}
            </span>
            {message.trust_tier === "DOCUMENT_FACT" && (
              <span className="badge-coverage">
                Coverage: {coveragePercent}%
              </span>
            )}
          </div>

          <p className="answer-body-text">{message.answer_text}</p>

          {/* Supporting Evidence Citations */}
          {message.evidence_references &&
            message.evidence_references.length > 0 && (
              <div className="qa-evidence-section">
                <span className="evidence-section-label">
                  Supporting Evidence:
                </span>
                <div className="evidence-badges-row">
                  {message.evidence_references.map((ev) => (
                    <EvidenceBadge
                      key={`${ev.claim_id}-${ev.page_start}`}
                      evidence={ev}
                      onInspect={onInspect}
                    />
                  ))}
                </div>
              </div>
            )}

          {/* Safety Notice if applicable */}
          <QASafetyNotice
            trustTier={message.trust_tier}
            safetyStatus={message.safety_status}
          />
        </div>
      </div>
    </article>
  );
};
