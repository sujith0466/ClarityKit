import React, { useState } from "react";
import {
  AssessedClaim,
  DocumentTrustReport,
  SafetyStatus,
  TrustTier,
} from "../../types/trust";

interface TrustSafetyViewerProps {
  report: DocumentTrustReport;
  documentFilename?: string;
  onClose?: () => void;
}

export const TrustSafetyViewer: React.FC<TrustSafetyViewerProps> = ({
  report,
  documentFilename,
  onClose,
}) => {
  const [tierFilter, setTierFilter] = useState<string>("ALL");
  const [selectedClaim, setSelectedClaim] = useState<AssessedClaim | null>(
    null
  );

  const filteredClaims = report.assessed_claims.filter((c) => {
    if (tierFilter === "ALL") return true;
    return c.trust_assessment.trust_tier === tierFilter;
  });

  const getTierBadgeClass = (tier: TrustTier): string => {
    switch (tier) {
      case "DOCUMENT_FACT":
        return "badge-tier-fact";
      case "GENERAL_INFORMATION":
        return "badge-tier-info";
      case "INTERPRETATION":
        return "badge-tier-interpretation";
      case "PROFESSIONAL_REVIEW_NEEDED":
        return "badge-tier-review";
      default:
        return "badge-tier-default";
    }
  };

  const getSafetyBadgeClass = (status: SafetyStatus): string => {
    switch (status) {
      case "SAFE":
        return "badge-safety-safe";
      case "LIMITED":
        return "badge-safety-limited";
      case "REVIEW_REQUIRED":
        return "badge-safety-review";
      case "UNSUPPORTED":
        return "badge-safety-unsupported";
      default:
        return "badge-safety-default";
    }
  };

  const formatTierLabel = (tier: TrustTier): string => {
    switch (tier) {
      case "DOCUMENT_FACT":
        return "Document Fact";
      case "GENERAL_INFORMATION":
        return "General Information";
      case "INTERPRETATION":
        return "Interpretation";
      case "PROFESSIONAL_REVIEW_NEEDED":
        return "Professional Review Needed";
      default:
        return tier;
    }
  };

  const formatSafetyLabel = (status: SafetyStatus): string => {
    switch (status) {
      case "SAFE":
        return "Safe";
      case "LIMITED":
        return "Limited";
      case "REVIEW_REQUIRED":
        return "Review Required";
      case "UNSUPPORTED":
        return "Unsupported";
      default:
        return status;
    }
  };

  return (
    <div
      className="trust-safety-viewer"
      data-testid="trust-safety-viewer"
      role="region"
      aria-label="Trust and Safety Assessment"
    >
      <div className="trust-viewer-header">
        <div>
          <h2 className="trust-title">
            Trust & Safety Assessment
            {documentFilename && (
              <span className="trust-filename"> — {documentFilename}</span>
            )}
          </h2>
          <p className="trust-subtitle">
            Deterministic classification separating verified document facts,
            interpretations, educational concepts, and items requiring
            professional legal review.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            className="btn-close-viewer"
            onClick={onClose}
            aria-label="Close Trust & Safety Viewer"
            data-testid="close-trust-viewer-btn"
          >
            &times;
          </button>
        )}
      </div>

      {/* Summary Metrics & Overall Status */}
      <div className="trust-metrics-card">
        <div className="metric-col">
          <span className="metric-label">Overall Safety Status</span>
          <span
            className={`badge-safety-lg ${getSafetyBadgeClass(
              report.overall_safety_status
            )}`}
            data-testid="overall-safety-badge"
          >
            {formatSafetyLabel(report.overall_safety_status)}
          </span>
        </div>

        <div className="metric-col">
          <span className="metric-label">Evidence Citation Coverage</span>
          <div className="coverage-meter-container">
            <span
              className="coverage-percent-text"
              data-testid="trust-coverage-text"
            >
              {(report.evidence_coverage * 100).toFixed(1)}%
            </span>
            <div
              className="coverage-progress-bar"
              role="progressbar"
              aria-valuenow={Math.round(report.evidence_coverage * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Evidence Citation Coverage Meter"
            >
              <div
                className="coverage-progress-fill"
                style={{
                  width: `${Math.min(
                    100,
                    Math.max(0, report.evidence_coverage * 100)
                  )}%`,
                }}
              />
            </div>
          </div>
          <span className="coverage-subtext">
            Measures mechanically valid citations. Does not imply legal advice
            or enforceability.
          </span>
        </div>

        <div className="metric-col">
          <span className="metric-label">Total Claims Evaluated</span>
          <span className="metric-val" data-testid="trust-total-claims">
            {report.total_claims}
          </span>
        </div>
      </div>

      {/* Tier Distribution Summary */}
      <div
        className="tier-breakdown-row"
        role="group"
        aria-label="Trust Tier Counts"
      >
        <div className="tier-summary-item fact">
          <span className="count">
            {report.tier_counts["DOCUMENT_FACT"] || 0}
          </span>
          <span className="label">Document Facts</span>
        </div>
        <div className="tier-summary-item info">
          <span className="count">
            {report.tier_counts["GENERAL_INFORMATION"] || 0}
          </span>
          <span className="label">General Info</span>
        </div>
        <div className="tier-summary-item interp">
          <span className="count">
            {report.tier_counts["INTERPRETATION"] || 0}
          </span>
          <span className="label">Interpretations</span>
        </div>
        <div className="tier-summary-item review">
          <span className="count">
            {report.tier_counts["PROFESSIONAL_REVIEW_NEEDED"] || 0}
          </span>
          <span className="label">Review Needed</span>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="trust-filters-row">
        <span className="filter-title">Filter by Trust Tier:</span>
        <div
          className="filter-btn-group"
          role="radiogroup"
          aria-label="Tier Filter"
        >
          {[
            "ALL",
            "DOCUMENT_FACT",
            "GENERAL_INFORMATION",
            "INTERPRETATION",
            "PROFESSIONAL_REVIEW_NEEDED",
          ].map((tier) => (
            <button
              key={tier}
              type="button"
              className={`btn-filter ${tierFilter === tier ? "active" : ""}`}
              onClick={() => setTierFilter(tier)}
              data-testid={`filter-tier-${tier.toLowerCase()}`}
              aria-pressed={tierFilter === tier}
            >
              {tier === "ALL"
                ? "All Claims"
                : formatTierLabel(tier as TrustTier)}
            </button>
          ))}
        </div>
      </div>

      {/* Claims List */}
      <div className="assessed-claims-list" data-testid="assessed-claims-list">
        {filteredClaims.length === 0 ? (
          <div className="empty-trust-state" data-testid="empty-trust-claims">
            No claims found matching the selected filter.
          </div>
        ) : (
          filteredClaims.map((claim) => {
            const assessment = claim.trust_assessment;
            return (
              <div
                key={claim.id}
                className={`assessed-claim-card tier-${assessment.trust_tier.toLowerCase()}`}
                data-testid={`assessed-claim-${claim.id}`}
              >
                <div className="claim-header-row">
                  <div className="claim-badges">
                    <span
                      className={`badge-tier ${getTierBadgeClass(
                        assessment.trust_tier
                      )}`}
                      data-testid={`badge-tier-${claim.id}`}
                    >
                      {formatTierLabel(assessment.trust_tier)}
                    </span>
                    <span
                      className={`badge-safety ${getSafetyBadgeClass(
                        assessment.safety_status
                      )}`}
                      data-testid={`badge-safety-${claim.id}`}
                    >
                      {formatSafetyLabel(assessment.safety_status)}
                    </span>
                    <span className="badge-type">{claim.claim_type}</span>
                  </div>

                  {claim.evidence && claim.evidence.length > 0 && (
                    <button
                      type="button"
                      className="btn-inspect-evidence"
                      onClick={() => setSelectedClaim(claim)}
                      data-testid={`inspect-evidence-btn-${claim.id}`}
                      aria-label={`Inspect evidence for claim ${claim.id}`}
                    >
                      Inspect Citations ({claim.evidence.length})
                    </button>
                  )}
                </div>

                <div className="claim-body-text">{claim.claim_text}</div>

                {assessment.reasoning_summary && (
                  <div className="claim-reasoning">
                    <strong>Safety Rationale:</strong>{" "}
                    {assessment.reasoning_summary}
                  </div>
                )}

                {assessment.limitations.length > 0 && (
                  <div className="claim-limitations-row">
                    <span className="limitations-label">Limitations:</span>
                    {assessment.limitations.map((lim) => (
                      <span
                        key={lim}
                        className="badge-limitation"
                        data-testid={`limitation-${lim.toLowerCase()}`}
                      >
                        {lim.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Prominent Legal Disclaimer */}
      <div
        className="trust-disclaimer-box"
        role="note"
        aria-label="Legal Disclaimer"
      >
        <strong>Important Safety Notice:</strong> {report.disclaimer}
      </div>

      {/* Citations Inspection Modal */}
      {selectedClaim && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="citations-modal-title"
        >
          <div className="modal-content citation-modal">
            <div className="modal-header">
              <h3 id="citations-modal-title">Citations for Claim</h3>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setSelectedClaim(null)}
                aria-label="Close citations modal"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-claim-text">"{selectedClaim.claim_text}"</p>
              <div className="modal-citations-list">
                {selectedClaim.evidence.map((ev, idx) => (
                  <div key={idx} className="modal-citation-card">
                    <div className="citation-meta-row">
                      <span className="citation-pages">
                        Page {ev.page_start}
                        {ev.page_end !== ev.page_start ? `–${ev.page_end}` : ""}
                      </span>
                      <span className={`badge-match-type ${ev.match_type}`}>
                        {ev.match_type}
                      </span>
                      <span
                        className={`badge-ev-status ${ev.validation_status}`}
                      >
                        {ev.validation_status}
                      </span>
                    </div>
                    <div className="citation-quote-box">"{ev.source_span}"</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedClaim(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
