import React from "react";
import { AnswerEvidenceSummary } from "../../types/qa";
import { InspectionTarget } from "../../types/workspace";

interface EvidenceBadgeProps {
  readonly evidence: AnswerEvidenceSummary;
  readonly onInspect: (target: InspectionTarget) => void;
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({
  evidence,
  onInspect,
}) => {
  const pageLabel =
    evidence.page_start === evidence.page_end
      ? `Page ${evidence.page_start}`
      : `Pages ${evidence.page_start}–${evidence.page_end}`;

  return (
    <button
      type="button"
      className="qa-evidence-badge"
      onClick={() =>
        onInspect({
          title: "Cited Document Evidence",
          claimText: evidence.claim_text,
          claimType: "document_fact",
          pageStart: evidence.page_start,
          pageEnd: evidence.page_end,
          sourceSpan: evidence.source_span,
          trustTier: "DOCUMENT_FACT",
          validationStatus: "VALID",
        })
      }
      title={`Inspect cited evidence on ${pageLabel}`}
      aria-label={`Inspect cited evidence on ${pageLabel}`}
      data-testid={`evidence-badge-${evidence.claim_id}`}
    >
      <span className="badge-icon" aria-hidden="true">
        &#128196;
      </span>
      <span className="badge-label">{pageLabel}</span>
      <span className="badge-action">Inspect &rarr;</span>
    </button>
  );
};
