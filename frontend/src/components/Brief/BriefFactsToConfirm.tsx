import React from "react";

interface BriefFactsToConfirmProps {
  readonly facts: readonly string[];
}

export const BriefFactsToConfirm: React.FC<BriefFactsToConfirmProps> = ({
  facts,
}) => {
  if (!facts || facts.length === 0) {
    return null;
  }

  return (
    <div className="brief-section-card">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">
          Facts to Confirm with Attorney
        </h3>
        <span className="brief-section-count">{facts.length} items</span>
      </div>
      <p className="brief-section-subtext">
        Verify these factual identities, execution states, and dates during your
        discussion:
      </p>

      <ul className="brief-checklist">
        {facts.map((fact, idx) => (
          <li key={`fact-${idx}`} className="brief-checklist-item">
            <span className="brief-checkbox-icon" aria-hidden="true">
              ☐
            </span>
            <span className="brief-checklist-text">{fact}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
