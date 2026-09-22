import React from "react";
import {
  ComparisonDocumentRef,
  ComparisonFinding,
  DifferenceClassification,
} from "../../types/comparison";
import { InspectionTarget } from "../../types/workspace";

interface SideBySideFindingCardProps {
  readonly finding: ComparisonFinding;
  readonly documents: readonly ComparisonDocumentRef[];
  readonly onInspect?: (target: InspectionTarget) => void;
}

const getClassificationLabel = (c: DifferenceClassification): string => {
  switch (c) {
    case "MATCH":
      return "Exact Match";
    case "DIFFERENT":
      return "Different Terms";
    case "PRESENT_IN_ONE_ONLY":
      return "Present in One Document Only";
    case "POTENTIAL_INCONSISTENCY":
      return "Potential Inconsistency";
    case "UNRESOLVED":
      return "Unresolved Fact";
    default:
      return c;
  }
};

const getClassificationBadgeClass = (c: DifferenceClassification): string => {
  switch (c) {
    case "MATCH":
      return "badge-status-match";
    case "DIFFERENT":
      return "badge-status-different";
    case "PRESENT_IN_ONE_ONLY":
      return "badge-status-one-only";
    case "POTENTIAL_INCONSISTENCY":
      return "badge-status-inconsistency";
    case "UNRESOLVED":
      return "badge-status-unresolved";
    default:
      return "badge-secondary";
  }
};

export const SideBySideFindingCard: React.FC<SideBySideFindingCardProps> = ({
  finding,
  documents,
  onInspect,
}) => {
  const handleInspectClick = (docId: string) => {
    const ev = finding.evidence_by_doc[docId];
    if (!ev || !onInspect) return;

    onInspect({
      title: `${finding.title} — ${ev.document_name}`,
      claimText: ev.exact_quote,
      claimType: finding.category.toLowerCase(),
      pageNumber: ev.page_number,
      sourceSpan: ev.exact_quote,
      validationStatus: ev.validation_status,
      matchType: ev.match_type,
    });
  };

  return (
    <article
      className={`comparison-finding-card finding-card-${finding.classification.toLowerCase()}`}
      data-testid={`finding-card-${finding.id}`}
      aria-labelledby={`finding-title-${finding.id}`}
    >
      <header className="finding-header">
        <div className="finding-title-row">
          <span className="finding-category-pill">
            {finding.category.replace(/_/g, " ")}
          </span>
          <span
            className={`badge ${getClassificationBadgeClass(finding.classification)}`}
          >
            {getClassificationLabel(finding.classification)}
          </span>
        </div>
        <h3 id={`finding-title-${finding.id}`} className="finding-title">
          {finding.title}
        </h3>
        <p className="finding-explanation">
          {finding.plain_english_explanation}
        </p>
      </header>

      {/* Side-by-side Evidence Grid */}
      <div
        className="finding-evidence-grid"
        style={{
          gridTemplateColumns: `repeat(${documents.length}, minmax(0, 1fr))`,
        }}
        role="region"
        aria-label="Side-by-side document evidence"
      >
        {documents.map((doc) => {
          const ev = finding.evidence_by_doc[doc.id];
          const hasEvidence = !!ev;

          return (
            <div
              key={doc.id}
              className={`evidence-doc-column ${hasEvidence ? "has-evidence" : "no-evidence"}`}
            >
              <div className="evidence-doc-header">
                <span className="evidence-doc-name" title={doc.filename}>
                  {doc.filename}
                </span>
                {hasEvidence && (
                  <span className="evidence-page-ref">
                    Page {ev.page_number}
                  </span>
                )}
              </div>

              <div className="evidence-doc-body">
                {hasEvidence ? (
                  <>
                    <blockquote className="evidence-quote">
                      &ldquo;{ev.exact_quote}&rdquo;
                    </blockquote>
                    <div className="evidence-meta-row">
                      <span
                        className="evidence-status-tag"
                        title={ev.validation_reason}
                      >
                        {ev.validation_status === "EXACT_MATCH"
                          ? "✓ Exact Quote"
                          : ev.validation_status}
                      </span>
                      {onInspect && (
                        <button
                          type="button"
                          className="btn-inspect-evidence"
                          onClick={() => handleInspectClick(doc.id)}
                          aria-label={`Inspect source text in ${doc.filename}`}
                        >
                          Inspect Source
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="evidence-missing-state">
                    <span className="missing-text-label">Not Identified</span>
                    <p className="missing-text-note">
                      No corresponding term found in extracted content.
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Neutral Consultation Question */}
      {finding.neutral_lawyer_question && (
        <div className="finding-lawyer-question-box">
          <div className="question-box-header">
            <span className="question-icon" aria-hidden="true">
              ⚖️
            </span>
            <strong>Question for Your Legal Professional</strong>
          </div>
          <p className="question-text">{finding.neutral_lawyer_question}</p>
        </div>
      )}

      {/* Next Steps */}
      {finding.suggested_next_steps.length > 0 && (
        <footer className="finding-next-steps">
          <span className="next-steps-heading">Suggested Preparation:</span>
          <ul className="next-steps-list">
            {finding.suggested_next_steps.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ul>
        </footer>
      )}
    </article>
  );
};
