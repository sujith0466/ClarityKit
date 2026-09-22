import React from "react";
import {
  VersionDiffFinding,
  VersionEvidenceRef,
} from "../../types/versionDiff";

interface SideBySideDiffCardProps {
  readonly finding: VersionDiffFinding;
  readonly v1Title: string;
  readonly v2Title: string;
  readonly onInspectSource: (
    ref: VersionEvidenceRef,
    finding: VersionDiffFinding
  ) => void;
}

export const SideBySideDiffCard: React.FC<SideBySideDiffCardProps> = ({
  finding,
  v1Title,
  v2Title,
  onInspectSource,
}) => {
  const getClassificationBadge = (cls: string) => {
    switch (cls) {
      case "ADDED":
        return <span className="diff-badge badge-added">Added in V2</span>;
      case "REMOVED":
        return <span className="diff-badge badge-removed">Removed in V2</span>;
      case "MODIFIED":
        return <span className="diff-badge badge-modified">Modified</span>;
      case "UNCHANGED":
        return <span className="diff-badge badge-unchanged">Unchanged</span>;
      case "POTENTIAL_CHANGE":
        return (
          <span className="diff-badge badge-potential">Potential Change</span>
        );
      default:
        return (
          <span className="diff-badge badge-unresolved">
            Professional Review Needed
          </span>
        );
    }
  };

  return (
    <article
      className={`diff-card side-by-side-card classification-${finding.classification.toLowerCase()}`}
      aria-labelledby={`finding-title-${finding.id}`}
    >
      <div className="diff-card-header">
        <div className="diff-card-header-left">
          <span className="diff-category-tag">{finding.category}</span>
          {getClassificationBadge(finding.classification)}
        </div>
        <div className="diff-card-header-right">
          <span className="trust-tier-badge">{finding.trust_tier}</span>
        </div>
      </div>

      <h3 id={`finding-title-${finding.id}`} className="diff-card-title">
        {finding.title}
      </h3>

      <p className="diff-card-description">{finding.description}</p>

      {/* Two Column Side-by-Side Delta Comparison */}
      <div className="side-by-side-grid">
        {/* Column 1: Base Version 1 */}
        <div className="version-column v1-column">
          <div className="column-header">
            <span className="col-version-tag">V1 (Base)</span>
            <span className="col-doc-title" title={v1Title}>
              {v1Title}
            </span>
          </div>

          <div className="column-content">
            {finding.v1_evidence.length > 0 ? (
              finding.v1_evidence.map((ev, idx) => (
                <div key={`v1-ev-${idx}`} className="evidence-snippet-box">
                  <blockquote className="evidence-quote">
                    "{ev.exact_quote || ev.source_span}"
                  </blockquote>
                  <div className="evidence-footer">
                    <span className="page-cite">
                      Pages {ev.page_start}
                      {ev.page_end !== ev.page_start ? `–${ev.page_end}` : ""}
                    </span>
                    <button
                      type="button"
                      className="btn-inspect-source"
                      onClick={() => onInspectSource(ev, finding)}
                      aria-label={`Inspect source text in Version 1 page ${ev.page_start}`}
                    >
                      Inspect Source
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-version-state">
                <em>Not present in Version 1</em>
              </div>
            )}
          </div>
        </div>

        {/* Column 2: Revised Version 2 */}
        <div className="version-column v2-column">
          <div className="column-header">
            <span className="col-version-tag">V2 (Revised)</span>
            <span className="col-doc-title" title={v2Title}>
              {v2Title}
            </span>
          </div>

          <div className="column-content">
            {finding.v2_evidence.length > 0 ? (
              finding.v2_evidence.map((ev, idx) => (
                <div key={`v2-ev-${idx}`} className="evidence-snippet-box">
                  <blockquote className="evidence-quote">
                    "{ev.exact_quote || ev.source_span}"
                  </blockquote>
                  <div className="evidence-footer">
                    <span className="page-cite">
                      Pages {ev.page_start}
                      {ev.page_end !== ev.page_start ? `–${ev.page_end}` : ""}
                    </span>
                    <button
                      type="button"
                      className="btn-inspect-source"
                      onClick={() => onInspectSource(ev, finding)}
                      aria-label={`Inspect source text in Version 2 page ${ev.page_start}`}
                    >
                      Inspect Source
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-version-state">
                <em>Omitted / Removed in Version 2</em>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Neutral Lawyer Preparation Questions */}
      {finding.lawyer_questions.length > 0 && (
        <div
          className="lawyer-questions-box"
          role="region"
          aria-label="Questions for Legal Counsel"
        >
          <h4 className="lawyer-questions-heading">
            Questions to Review with Counsel:
          </h4>
          <ul className="lawyer-questions-list">
            {finding.lawyer_questions.map((q, idx) => (
              <li key={idx} className="lawyer-question-item">
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
};
