import React from "react";

interface BriefSafetyNoticeProps {
  readonly disclaimer?: string;
}

export const BriefSafetyNotice: React.FC<BriefSafetyNoticeProps> = ({
  disclaimer,
}) => {
  const noticeText =
    disclaimer ||
    "IMPORTANT NOTICE: This preparation brief is an evidence-grounded aid designed " +
      "to help you prepare for a consultation with a qualified legal professional. It does " +
      "NOT constitute legal advice, a legal opinion, or an enforceability prediction. " +
      "Always consult a licensed attorney in your jurisdiction for specific legal counsel.";

  return (
    <div
      className="brief-safety-notice"
      role="region"
      aria-label="Legal Consultation Notice"
    >
      <div className="brief-safety-notice-header">
        <span className="brief-safety-icon" aria-hidden="true">
          ℹ️
        </span>
        <strong className="brief-safety-title">
          CONSULTATION PREPARATION AID — NOT LEGAL ADVICE
        </strong>
      </div>
      <p className="brief-safety-text">{noticeText}</p>
    </div>
  );
};
