import React, { useState } from "react";
import { ExtractedClause } from "../../types/extraction";
import { InspectionTarget } from "../../types/workspace";

interface ClausesViewProps {
  clauses: readonly ExtractedClause[];
  onInspect: (target: InspectionTarget) => void;
}

export const ClausesView: React.FC<ClausesViewProps> = ({
  clauses,
  onInspect,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  if (!clauses || clauses.length === 0) {
    return (
      <div className="empty-state-card" data-testid="empty-clauses">
        <p className="empty-title">No Clauses Extracted</p>
        <p className="empty-desc">
          No clauses were extracted from this document.
        </p>
      </div>
    );
  }

  const categories = Array.from(
    new Set(clauses.map((c) => c.category || "general"))
  ).sort();

  const filteredClauses =
    selectedCategory === "ALL"
      ? clauses
      : clauses.filter((c) => (c.category || "general") === selectedCategory);

  return (
    <div className="workspace-panel" data-testid="clauses-view">
      <div className="panel-header">
        <h2 className="panel-title">Clause Explorer ({clauses.length})</h2>
        <p className="panel-desc">
          Categorized legal clauses and provisions with source citations.
        </p>
      </div>

      <div
        className="category-filter-row"
        data-testid="clause-category-filters"
      >
        <button
          type="button"
          className={`filter-chip ${selectedCategory === "ALL" ? "active" : ""}`}
          onClick={() => setSelectedCategory("ALL")}
          data-testid="filter-clause-all"
        >
          All ({clauses.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`filter-chip ${selectedCategory === cat ? "active" : ""}`}
            onClick={() => setSelectedCategory(cat)}
            data-testid={`filter-clause-${cat}`}
          >
            {cat} (
            {clauses.filter((c) => (c.category || "general") === cat).length})
          </button>
        ))}
      </div>

      {filteredClauses.length === 0 ? (
        <div className="empty-state-card">
          <p className="empty-desc">No clauses found in this category.</p>
        </div>
      ) : (
        <div className="clauses-list">
          {filteredClauses.map((clause) => (
            <div
              key={clause.id}
              className="clause-card"
              data-testid={`clause-card-${clause.id}`}
            >
              <div className="clause-header">
                <div className="clause-title-group">
                  <h3 className="clause-title">{clause.title}</h3>
                  <span className="badge-category">{clause.category}</span>
                </div>
                <span className="badge-tier">DOCUMENT_FACT</span>
              </div>
              <p className="clause-text">{clause.text}</p>
              <div className="card-source-row">
                <span className="source-page">
                  {clause.page_start === clause.page_end
                    ? `Page ${clause.page_start}`
                    : `Pages ${clause.page_start}–${clause.page_end}`}
                </span>
                <button
                  type="button"
                  className="btn-inspect-sm"
                  onClick={() =>
                    onInspect({
                      title: clause.title,
                      claimText: clause.text,
                      claimType: "clause",
                      pageStart: clause.page_start,
                      pageEnd: clause.page_end,
                      sourceSpan: clause.source_span || clause.text,
                      trustTier: "DOCUMENT_FACT",
                    })
                  }
                  data-testid={`inspect-clause-${clause.id}`}
                  aria-label={`Inspect source for ${clause.title}`}
                >
                  Inspect Source
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
