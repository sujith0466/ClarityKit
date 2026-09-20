import React from "react";
import { DocumentUnderstanding } from "../../types/extraction";
import { DocumentEvidenceReport } from "../../types/evidence";
import { DocumentTrustReport } from "../../types/trust";
import { WorkspaceTab } from "../../types/workspace";

interface WorkspaceOverviewProps {
  understanding: DocumentUnderstanding | null;
  evidenceReport: DocumentEvidenceReport | null;
  trustReport: DocumentTrustReport | null;
  onSelectTab: (tab: WorkspaceTab) => void;
}

export const WorkspaceOverview: React.FC<WorkspaceOverviewProps> = ({
  understanding,
  evidenceReport,
  trustReport,
  onSelectTab,
}) => {
  const partiesCount = understanding?.parties.length || 0;
  const clausesCount = understanding?.clauses.length || 0;
  const obligationsCount = understanding?.obligations.length || 0;
  const datesCount = understanding?.dates.length || 0;
  const reviewFlagsCount = understanding?.review_flags.length || 0;

  const coverageRatio =
    trustReport?.evidence_coverage ??
    evidenceReport?.coverage.coverage_ratio ??
    0;
  const coveragePercent = Math.round(coverageRatio * 100);

  return (
    <div
      className="workspace-overview-container"
      data-testid="workspace-overview"
    >
      <section className="overview-hero-section">
        <h2 className="overview-section-title">
          Document Summary &amp; Profile
        </h2>
        <p className="overview-section-subtitle">
          Structured understanding, verified citations, and safety
          classifications derived from authoritative document pages.
        </p>

        <div className="coverage-card" data-testid="overview-coverage-card">
          <div className="coverage-header">
            <span className="coverage-label">Evidence Coverage:</span>
            <span
              className="coverage-value"
              data-testid="overview-coverage-value"
            >
              {coveragePercent}%
            </span>
          </div>
          <div
            className="coverage-progress-bar-bg"
            role="progressbar"
            aria-valuenow={coveragePercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Document evidence coverage percentage"
          >
            <div
              className="coverage-progress-bar-fill"
              style={{ width: `${coveragePercent}%` }}
            />
          </div>
          <span className="coverage-caption">
            Percentage of extracted claims backed by mechanically validated
            citations.
          </span>
        </div>
      </section>

      <section className="overview-cards-grid">
        {/* Parties Card */}
        <div
          className="overview-metric-card"
          data-testid="overview-card-parties"
        >
          <div className="card-header-row">
            <h3 className="card-title">Parties</h3>
            <span className="metric-badge">{partiesCount}</span>
          </div>
          <p className="card-desc">
            Identified contracting entities and designated roles.
          </p>
          <div className="card-preview-list">
            {understanding?.parties.slice(0, 3).map((party) => (
              <div key={party.id} className="preview-item">
                <span className="item-name font-bold">{party.name}</span>
                <span className="item-sub">
                  Role: {party.role || "Not specified"}
                </span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("parties")}
            data-testid="jump-parties-btn"
          >
            View All Parties &rarr;
          </button>
        </div>

        {/* Clauses Card */}
        <div
          className="overview-metric-card"
          data-testid="overview-card-clauses"
        >
          <div className="card-header-row">
            <h3 className="card-title">Clauses</h3>
            <span className="metric-badge">{clausesCount}</span>
          </div>
          <p className="card-desc">
            Categorized legal provisions and contractual sections.
          </p>
          <div className="card-preview-list">
            {understanding?.clauses.slice(0, 3).map((clause) => (
              <div key={clause.id} className="preview-item">
                <span className="item-name font-bold">{clause.title}</span>
                <span className="item-sub">Category: {clause.category}</span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("clauses")}
            data-testid="jump-clauses-btn"
          >
            Explore Clauses &rarr;
          </button>
        </div>

        {/* Obligations Card */}
        <div
          className="overview-metric-card"
          data-testid="overview-card-obligations"
        >
          <div className="card-header-row">
            <h3 className="card-title">Key Obligations</h3>
            <span className="metric-badge">{obligationsCount}</span>
          </div>
          <p className="card-desc">
            Actionable duties, conditions, and compliance requirements.
          </p>
          <div className="card-preview-list">
            {understanding?.obligations.slice(0, 3).map((ob) => (
              <div key={ob.id} className="preview-item">
                <span className="item-name font-bold">{ob.obligor}:</span>
                <span className="item-sub">{ob.duty}</span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("obligations")}
            data-testid="jump-obligations-btn"
          >
            View Obligations &rarr;
          </button>
        </div>

        {/* Dates Card */}
        <div className="overview-metric-card" data-testid="overview-card-dates">
          <div className="card-header-row">
            <h3 className="card-title">Important Dates</h3>
            <span className="metric-badge">{datesCount}</span>
          </div>
          <p className="card-desc">
            Extracted execution, notice, renewal, and expiration dates.
          </p>
          <div className="card-preview-list">
            {understanding?.dates.slice(0, 3).map((dt) => (
              <div key={dt.id} className="preview-item">
                <span className="item-name font-bold">{dt.raw_text}</span>
                <span className="item-sub">
                  {dt.description || dt.date_type}
                </span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("dates")}
            data-testid="jump-dates-btn"
          >
            View Dates &rarr;
          </button>
        </div>

        {/* Review Areas Card */}
        <div
          className="overview-metric-card"
          data-testid="overview-card-review"
        >
          <div className="card-header-row">
            <h3 className="card-title">Attention Areas</h3>
            <span className="metric-badge warning">{reviewFlagsCount}</span>
          </div>
          <p className="card-desc">
            Items identified for closer inspection or professional review.
          </p>
          <div className="card-preview-list">
            {understanding?.review_flags.slice(0, 3).map((flag) => (
              <div key={flag.id} className="preview-item">
                <span className="item-name font-bold text-amber-700">
                  {flag.title}
                </span>
                <span className="item-sub">{flag.description}</span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("review_areas")}
            data-testid="jump-review-btn"
          >
            Inspect Review Areas &rarr;
          </button>
        </div>

        {/* Trust & Safety Summary Card */}
        <div className="overview-metric-card" data-testid="overview-card-trust">
          <div className="card-header-row">
            <h3 className="card-title">Trust &amp; Safety</h3>
            <span className="badge-tier">
              {trustReport?.overall_safety_status || "SAFE"}
            </span>
          </div>
          <p className="card-desc">
            Deterministic trust tiers and material limitations.
          </p>
          <div className="trust-tier-mini-grid">
            <div className="tier-mini-badge fact">
              <span className="count">
                {trustReport?.tier_counts?.DOCUMENT_FACT ?? 0}
              </span>
              <span className="label">Document Facts</span>
            </div>
            <div className="tier-mini-badge review">
              <span className="count">
                {trustReport?.tier_counts?.PROFESSIONAL_REVIEW_NEEDED ?? 0}
              </span>
              <span className="label">Review Needed</span>
            </div>
          </div>
          <button
            type="button"
            className="btn-card-action"
            onClick={() => onSelectTab("trust")}
            data-testid="jump-trust-btn"
          >
            View Trust Report &rarr;
          </button>
        </div>
      </section>

      <div className="workspace-disclaimer-box">
        <strong>Important Notice:</strong> ClarityKit is an AI-powered legal
        document understanding assistant and does not provide legal advice. All
        document-specific claims are mapped to authoritative citations for
        manual verification.
      </div>
    </div>
  );
};
