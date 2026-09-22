import React from "react";
import {
  VersionDiffFinding,
  VersionEvidenceRef,
} from "../../types/versionDiff";

interface UnifiedDiffCardProps {
  readonly finding: VersionDiffFinding;
  readonly v1Title: string;
  readonly v2Title: string;
  readonly onInspectSource: (
    ref: VersionEvidenceRef,
    finding: VersionDiffFinding
  ) => void;
}

export const UnifiedDiffCard: React.FC<UnifiedDiffCardProps> = ({
  finding,
  v1Title,
  v2Title,
  onInspectSource,
}) => {
  return (
    <article
      className={`diff-card unified-card classification-${finding.classification.toLowerCase()}`}
      aria-labelledby={`unified-title-${finding.id}`}
    >
      <div className="diff-card-header">
        <div className="diff-card-header-left">
          <span className="diff-category-tag">{finding.category}</span>
          <span
            className={`diff-badge badge-${finding.classification.toLowerCase()}`}
          >
            {finding.classification}
          </span>
        </div>
        <div className="diff-card-header-right">
          <span className="trust-tier-badge">{finding.trust_tier}</span>
        </div>
      </div>

      <h3 id={`unified-title-${finding.id}`} className="diff-card-title">
        {finding.title}
      </h3>

      <p className="diff-card-description">{finding.description}</p>

      {/* Unified linear stream */}
      <div className="unified-stream">
        {/* Version 1 Evidence */}
        {finding.v1_evidence.map((ev, idx) => (
          <div key={`u-v1-${idx}`} className="unified-row v1-row">
            <div className="row-indicator v1-indicator">
              <span className="indicator-symbol">-</span>
              <span className="indicator-label">
                V1: {v1Title} (Page {ev.page_start})
              </span>
            </div>
            <div className="row-content">
              <blockquote className="unified-quote">
                "{ev.exact_quote || ev.source_span}"
              </blockquote>
              <button
                type="button"
                className="btn-inspect-source"
                onClick={() => onInspectSource(ev, finding)}
              >
                Inspect Source
              </button>
            </div>
          </div>
        ))}

        {/* Version 2 Evidence */}
        {finding.v2_evidence.map((ev, idx) => (
          <div key={`u-v2-${idx}`} className="unified-row v2-row">
            <div className="row-indicator v2-indicator">
              <span className="indicator-symbol">+</span>
              <span className="indicator-label">
                V2: {v2Title} (Page {ev.page_start})
              </span>
            </div>
            <div className="row-content">
              <blockquote className="unified-quote">
                "{ev.exact_quote || ev.source_span}"
              </blockquote>
              <button
                type="button"
                className="btn-inspect-source"
                onClick={() => onInspectSource(ev, finding)}
              >
                Inspect Source
              </button>
            </div>
          </div>
        ))}
      </div>

      {finding.lawyer_questions.length > 0 && (
        <div className="lawyer-questions-box">
          <h4 className="lawyer-questions-heading">Counsel Questions:</h4>
          <ul className="lawyer-questions-list">
            {finding.lawyer_questions.map((q, idx) => (
              <li key={idx}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
};
