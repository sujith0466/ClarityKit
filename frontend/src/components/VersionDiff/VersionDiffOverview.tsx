import React from "react";
import {
  VersionDiffCategory,
  VersionDiffClassification,
  VersionDiffSummary,
} from "../../types/versionDiff";

interface VersionDiffOverviewProps {
  readonly summary: VersionDiffSummary;
  readonly activeCategory: VersionDiffCategory | "ALL";
  readonly activeClassification: VersionDiffClassification | "ALL";
  readonly viewMode: "side-by-side" | "unified";
  readonly onSelectCategory: (cat: VersionDiffCategory | "ALL") => void;
  readonly onSelectClassification: (
    cls: VersionDiffClassification | "ALL"
  ) => void;
  readonly onToggleViewMode: (mode: "side-by-side" | "unified") => void;
}

export const VersionDiffOverview: React.FC<VersionDiffOverviewProps> = ({
  summary,
  activeCategory,
  activeClassification,
  viewMode,
  onSelectCategory,
  onSelectClassification,
  onToggleViewMode,
}) => {
  const categories: (VersionDiffCategory | "ALL")[] = [
    "ALL",
    "PARTIES",
    "DATES",
    "OBLIGATIONS",
    "CLAUSES",
    "NOTICE",
    "GENERAL",
  ];

  const classifications: {
    id: VersionDiffClassification | "ALL";
    label: string;
    count: number;
  }[] = [
    { id: "ALL", label: "All Deltas", count: summary.total_findings },
    { id: "ADDED", label: "Added in V2", count: summary.added_count },
    { id: "REMOVED", label: "Removed in V2", count: summary.removed_count },
    { id: "MODIFIED", label: "Modified", count: summary.modified_count },
    { id: "UNCHANGED", label: "Unchanged", count: summary.unchanged_count },
    {
      id: "POTENTIAL_CHANGE",
      label: "Potential Changes",
      count: summary.potential_change_count,
    },
    {
      id: "UNRESOLVED",
      label: "Unresolved",
      count: summary.unresolved_count,
    },
  ];

  return (
    <section
      className="version-diff-overview"
      aria-label="Version Diff Overview"
    >
      {/* Metric Cards */}
      <div className="diff-metrics-grid">
        <div className="metric-box total">
          <span className="metric-num">{summary.total_findings}</span>
          <span className="metric-label">Total Elements</span>
        </div>
        <div className="metric-box added">
          <span className="metric-num">{summary.added_count}</span>
          <span className="metric-label">Added</span>
        </div>
        <div className="metric-box removed">
          <span className="metric-num">{summary.removed_count}</span>
          <span className="metric-label">Removed</span>
        </div>
        <div className="metric-box modified">
          <span className="metric-num">{summary.modified_count}</span>
          <span className="metric-label">Modified</span>
        </div>
        <div className="metric-box unchanged">
          <span className="metric-num">{summary.unchanged_count}</span>
          <span className="metric-label">Unchanged</span>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="diff-controls-bar">
        {/* Classification Filters */}
        <div
          className="classification-filters"
          role="group"
          aria-label="Filter by change type"
        >
          {classifications.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`filter-pill ${activeClassification === item.id ? "active" : ""}`}
              onClick={() => onSelectClassification(item.id)}
              aria-pressed={activeClassification === item.id}
            >
              {item.label} ({item.count})
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div
          className="view-mode-toggle"
          role="radiogroup"
          aria-label="Diff view layout"
        >
          <button
            type="button"
            className={`view-mode-btn ${viewMode === "side-by-side" ? "active" : ""}`}
            onClick={() => onToggleViewMode("side-by-side")}
            role="radio"
            aria-checked={viewMode === "side-by-side"}
          >
            Side-by-Side
          </button>
          <button
            type="button"
            className={`view-mode-btn ${viewMode === "unified" ? "active" : ""}`}
            onClick={() => onToggleViewMode("unified")}
            role="radio"
            aria-checked={viewMode === "unified"}
          >
            Unified
          </button>
        </div>
      </div>

      {/* Category Pills */}
      <div
        className="category-filters-row"
        role="group"
        aria-label="Filter by category"
      >
        <span className="category-filter-label">Categories:</span>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`cat-pill ${activeCategory === cat ? "active" : ""}`}
            onClick={() => onSelectCategory(cat)}
            aria-pressed={activeCategory === cat}
          >
            {cat}
          </button>
        ))}
      </div>
    </section>
  );
};
