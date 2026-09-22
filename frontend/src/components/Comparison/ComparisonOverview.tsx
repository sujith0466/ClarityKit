import React from "react";
import {
  ComparisonCategory,
  ComparisonSummary,
  DifferenceClassification,
} from "../../types/comparison";

interface ComparisonOverviewProps {
  readonly summary: ComparisonSummary;
  readonly activeCategory: ComparisonCategory | "ALL";
  readonly onCategoryChange: (category: ComparisonCategory | "ALL") => void;
  readonly activeClassification: DifferenceClassification | "ALL";
  readonly onClassificationChange: (
    classification: DifferenceClassification | "ALL"
  ) => void;
  readonly disclaimer: string;
}

const CATEGORIES: {
  readonly value: ComparisonCategory | "ALL";
  readonly label: string;
}[] = [
  { value: "ALL", label: "All Categories" },
  { value: "PARTIES", label: "Parties" },
  { value: "EFFECTIVE_DATE", label: "Effective Dates" },
  { value: "TERMINATION_DATE", label: "Termination Dates" },
  { value: "NOTICE_PERIOD", label: "Notice Periods" },
  { value: "FINANCIAL_TERMS", label: "Financial Terms" },
  { value: "GOVERNING_LAW", label: "Governing Law" },
  { value: "DISPUTE_RESOLUTION", label: "Dispute Resolution" },
  { value: "CONFIDENTIALITY", label: "Confidentiality" },
  { value: "LIABILITY", label: "Liability" },
  { value: "CLAUSE_STRUCTURE", label: "Clause Structure" },
];

const CLASSIFICATIONS: {
  readonly value: DifferenceClassification | "ALL";
  readonly label: string;
}[] = [
  { value: "ALL", label: "All Classifications" },
  { value: "MATCH", label: "Exact Matches" },
  { value: "DIFFERENT", label: "Differences" },
  { value: "POTENTIAL_INCONSISTENCY", label: "Potential Inconsistencies" },
  { value: "PRESENT_IN_ONE_ONLY", label: "Present in One Only" },
];

export const ComparisonOverview: React.FC<ComparisonOverviewProps> = ({
  summary,
  activeCategory,
  onCategoryChange,
  activeClassification,
  onClassificationChange,
  disclaimer,
}) => {
  return (
    <div
      className="comparison-overview-section"
      data-testid="comparison-overview"
    >
      {/* Statutory / Trust & Safety Boundary Notice */}
      <div
        className="comparison-disclaimer-banner"
        role="region"
        aria-label="Legal Disclaimer"
      >
        <div className="disclaimer-header">
          <span className="disclaimer-icon" aria-hidden="true">
            ℹ️
          </span>
          <strong>Informational Comparison Only — Not Legal Advice</strong>
        </div>
        <p className="disclaimer-body">{disclaimer}</p>
      </div>

      {/* Summary Metrics */}
      <div
        className="comparison-metrics-grid"
        role="region"
        aria-label="Comparison Metrics"
      >
        <div className="metric-card metric-total">
          <span className="metric-value">{summary.total_findings}</span>
          <span className="metric-label">Total Findings</span>
        </div>
        <div className="metric-card metric-matches">
          <span className="metric-value">{summary.total_matches}</span>
          <span className="metric-label">Matching Terms</span>
        </div>
        <div className="metric-card metric-differences">
          <span className="metric-value">{summary.total_differences}</span>
          <span className="metric-label">Differing Terms</span>
        </div>
        <div className="metric-card metric-inconsistencies">
          <span className="metric-value">{summary.total_inconsistencies}</span>
          <span className="metric-label">Potential Inconsistencies</span>
        </div>
        <div className="metric-card metric-one-only">
          <span className="metric-value">
            {summary.total_present_in_one_only}
          </span>
          <span className="metric-label">Present in One Only</span>
        </div>
      </div>

      {/* Filters Bar */}
      <div
        className="comparison-filters-bar"
        role="toolbar"
        aria-label="Filter comparison findings"
      >
        <div className="filter-group">
          <label htmlFor="category-filter" className="filter-label">
            Category:
          </label>
          <select
            id="category-filter"
            className="filter-select"
            value={activeCategory}
            onChange={(e) =>
              onCategoryChange(e.target.value as ComparisonCategory | "ALL")
            }
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="classification-filter" className="filter-label">
            Classification:
          </label>
          <select
            id="classification-filter"
            className="filter-select"
            value={activeClassification}
            onChange={(e) =>
              onClassificationChange(
                e.target.value as DifferenceClassification | "ALL"
              )
            }
          >
            {CLASSIFICATIONS.map((cls) => (
              <option key={cls.value} value={cls.value}>
                {cls.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};
