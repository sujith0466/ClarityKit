import React, { useState, useId } from "react";
import {
  Claim,
  ClaimType,
  DocumentEvidenceReport,
  EvidenceValidationStatus,
} from "../../types/evidence";

interface EvidenceViewerProps {
  readonly report: DocumentEvidenceReport;
  readonly documentFilename: string;
  readonly onClose: () => void;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  report,
  documentFilename,
  onClose,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [inspectingClaim, setInspectingClaim] = useState<Claim | null>(null);

  const headingId = useId();
  const modalHeadingId = useId();

  const { claims, coverage, disclaimer } = report;

  // Filter claims
  const filteredClaims = claims.filter((c) => {
    if (selectedStatus !== "ALL" && c.validation_status !== selectedStatus) {
      return false;
    }
    if (selectedType !== "ALL" && c.claim_type !== selectedType) {
      return false;
    }
    return true;
  });

  const getStatusBadge = (
    status: EvidenceValidationStatus,
    matchType?: string,
    reason?: string | null
  ) => {
    if (status === "VALID") {
      return (
        <span className="badge badge-valid" role="status">
          <span className="badge-icon" aria-hidden="true">
            ✓
          </span>
          VALID ({matchType || "exact"})
        </span>
      );
    }
    if (status === "INVALID") {
      return (
        <span className="badge badge-invalid" role="status">
          <span className="badge-icon" aria-hidden="true">
            ⚠
          </span>
          INVALID{reason ? `: ${reason}` : ""}
        </span>
      );
    }
    return (
      <span className="badge badge-unverified" role="status">
        UNVERIFIED
      </span>
    );
  };

  const getClaimTypeLabel = (type: ClaimType): string => {
    switch (type) {
      case "party":
        return "Party";
      case "clause":
        return "Clause";
      case "obligation":
        return "Obligation";
      case "date":
        return "Date";
      case "review_flag":
        return "Review Flag";
      default:
        return "General Fact";
    }
  };

  return (
    <div
      className="evidence-viewer-container"
      role="region"
      aria-labelledby={headingId}
      data-testid="evidence-viewer"
    >
      <div className="evidence-header">
        <div>
          <h2 id={headingId} className="evidence-title">
            Evidence Engine: Citation Verification
          </h2>
          <p className="evidence-subtitle">
            Document: <strong>{documentFilename}</strong>
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={onClose}
          aria-label="Close evidence viewer"
          data-testid="close-evidence-viewer-btn"
        >
          Close
        </button>
      </div>

      {/* Coverage and Disclaimer Banner */}
      <div className="coverage-card" data-testid="coverage-card">
        <div className="coverage-header">
          <div>
            <span className="coverage-label">Evidence Coverage</span>
            <div className="coverage-value" data-testid="coverage-percentage">
              {coverage.coverage_percentage}%
            </div>
          </div>
          <div className="coverage-stats">
            <span className="coverage-stat-item">
              <strong>{coverage.valid_claims}</strong> valid
            </span>
            <span className="coverage-divider">/</span>
            <span className="coverage-stat-item">
              <strong>{coverage.total_claims}</strong> total claims
            </span>
          </div>
        </div>

        <div
          className="progress-bar-container"
          role="progressbar"
          aria-valuenow={coverage.coverage_percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Evidence coverage percentage"
        >
          <div
            className={`progress-bar-fill ${
              coverage.is_fully_covered
                ? "progress-fill-full"
                : "progress-fill-partial"
            }`}
            style={{
              width: `${Math.min(100, Math.max(0, coverage.coverage_percentage))}%`,
            }}
          />
        </div>

        <p className="coverage-note">
          Evidence coverage: {coverage.coverage_percentage}% of
          document-specific claims have a valid source reference.
        </p>

        <div
          className="evidence-disclaimer-banner"
          role="note"
          data-testid="evidence-disclaimer"
        >
          <span className="disclaimer-icon" aria-hidden="true">
            ℹ
          </span>
          <span>{disclaimer}</span>
        </div>
      </div>

      {/* Controls & Filters */}
      <div className="evidence-filter-bar">
        <div className="filter-group">
          <label htmlFor="filter-status-select" className="filter-label">
            Status:
          </label>
          <select
            id="filter-status-select"
            className="filter-select"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            data-testid="filter-status"
          >
            <option value="ALL">All Statuses ({claims.length})</option>
            <option value="VALID">Valid ({coverage.valid_claims})</option>
            <option value="INVALID">Invalid ({coverage.invalid_claims})</option>
            <option value="UNVERIFIED">
              Unverified ({coverage.unverified_claims})
            </option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-type-select" className="filter-label">
            Claim Type:
          </label>
          <select
            id="filter-type-select"
            className="filter-select"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            data-testid="filter-type"
          >
            <option value="ALL">All Types</option>
            <option value="party">Parties</option>
            <option value="clause">Clauses</option>
            <option value="obligation">Obligations</option>
            <option value="date">Dates</option>
            <option value="review_flag">Review Flags</option>
            <option value="general_fact">General Facts</option>
          </select>
        </div>
      </div>

      {/* Claims List */}
      <div
        className="evidence-claims-list"
        role="feed"
        aria-label="Claims and Evidence List"
      >
        {filteredClaims.length === 0 ? (
          <div
            className="empty-evidence-message"
            data-testid="empty-evidence-message"
          >
            No claims match the selected filter criteria.
          </div>
        ) : (
          filteredClaims.map((claim, idx) => {
            const ev = claim.evidence;
            return (
              <article
                key={claim.id || `claim-${idx}`}
                className={`claim-card ${
                  claim.validation_status === "VALID"
                    ? "claim-card-valid"
                    : "claim-card-invalid"
                }`}
                data-testid={`claim-card-${claim.id}`}
              >
                <div className="claim-card-header">
                  <div className="claim-meta-tags">
                    <span className="badge badge-type">
                      {getClaimTypeLabel(claim.claim_type)}
                    </span>
                    {ev && (
                      <span className="badge badge-page">
                        {ev.page_start === ev.page_end
                          ? `Page ${ev.page_start}`
                          : `Pages ${ev.page_start}–${ev.page_end}`}
                      </span>
                    )}
                  </div>
                  {getStatusBadge(
                    claim.validation_status,
                    ev?.match_type,
                    ev?.validation_reason
                  )}
                </div>

                <div className="claim-body">
                  <h3 className="claim-text">{claim.claim_text}</h3>

                  {ev ? (
                    <div className="source-span-box">
                      <div className="source-span-header">
                        <span className="source-span-title">
                          Cited Source Span:
                        </span>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() => setInspectingClaim(claim)}
                          aria-label={`Inspect source text for ${claim.claim_text}`}
                          data-testid={`inspect-btn-${claim.id}`}
                        >
                          Inspect Source Snippet
                        </button>
                      </div>
                      <blockquote className="source-span-quote">
                        "{ev.source_span}"
                      </blockquote>
                      {ev.source_text && ev.source_text !== ev.source_span && (
                        <div className="source-text-resolved">
                          <span className="resolved-label">
                            Resolved Document Text:
                          </span>
                          <span className="resolved-content">
                            "{ev.source_text}"
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="no-evidence-alert" role="alert">
                      ⚠ No evidence reference provided. Non-compliant with
                      zero-evidence policy.
                    </div>
                  )}
                </div>
              </article>
            );
          })
        )}
      </div>

      {/* Inspect Source Modal */}
      {inspectingClaim && inspectingClaim.evidence && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby={modalHeadingId}
        >
          <div className="modal-card">
            <div className="modal-header">
              <h3 id={modalHeadingId} className="modal-title">
                Source Span Inspection
              </h3>
              <button
                type="button"
                className="btn-close"
                onClick={() => setInspectingClaim(null)}
                aria-label="Close source inspector"
                data-testid="close-source-inspector"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-claim-summary">
                <strong>Claim:</strong> {inspectingClaim.claim_text}
              </p>
              <div className="modal-meta-row">
                <span>
                  <strong>Location:</strong>{" "}
                  {inspectingClaim.evidence.page_start ===
                  inspectingClaim.evidence.page_end
                    ? `Page ${inspectingClaim.evidence.page_start}`
                    : `Pages ${inspectingClaim.evidence.page_start}–${inspectingClaim.evidence.page_end}`}
                </span>
                <span>
                  <strong>Status:</strong> {inspectingClaim.validation_status}
                </span>
                <span>
                  <strong>Match Type:</strong>{" "}
                  {inspectingClaim.evidence.match_type}
                </span>
              </div>
              <div className="modal-source-view">
                <span className="source-view-label">
                  Authoritative Source Passage:
                </span>
                <pre className="source-view-content" tabIndex={0}>
                  {inspectingClaim.evidence.source_text ||
                    inspectingClaim.evidence.source_span}
                </pre>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-primary"
                onClick={() => setInspectingClaim(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
