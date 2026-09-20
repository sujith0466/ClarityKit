import React from "react";

interface QASafetyNoticeProps {
  readonly trustTier: string;
  readonly safetyStatus: string;
}

export const QASafetyNotice: React.FC<QASafetyNoticeProps> = ({
  trustTier,
  safetyStatus,
}) => {
  if (
    trustTier === "PROFESSIONAL_REVIEW_NEEDED" ||
    safetyStatus === "REVIEW_REQUIRED" ||
    safetyStatus === "UNSUPPORTED"
  ) {
    return (
      <div
        className="qa-safety-notice review-needed"
        role="alert"
        data-testid="qa-safety-notice"
      >
        <span className="notice-icon" aria-hidden="true">
          &#9888;
        </span>
        <div className="notice-content">
          <strong>Professional Review Needed:</strong> This question depends on
          facts, legal considerations, or enforceability questions that are not
          established by the provided document. Consider discussing it with a
          qualified legal professional.
        </div>
      </div>
    );
  }

  if (trustTier === "INTERPRETATION" || safetyStatus === "LIMITED") {
    return (
      <div
        className="qa-safety-notice interpretation"
        role="note"
        data-testid="qa-safety-notice"
      >
        <span className="notice-icon" aria-hidden="true">
          &#8505;
        </span>
        <div className="notice-content">
          <strong>Document Interpretation:</strong> This explanation is based on
          the phrasing of the contract terms and is provided for informational
          purposes only.
        </div>
      </div>
    );
  }

  return null;
};
