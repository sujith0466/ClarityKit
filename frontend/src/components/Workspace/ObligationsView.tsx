import React, { useState } from "react";
import { ExtractedObligation } from "../../types/extraction";
import { InspectionTarget } from "../../types/workspace";

interface ObligationsViewProps {
  obligations: readonly ExtractedObligation[];
  onInspect: (target: InspectionTarget) => void;
}

export const ObligationsView: React.FC<ObligationsViewProps> = ({
  obligations,
  onInspect,
}) => {
  const [selectedParty, setSelectedParty] = useState<string>("ALL");

  if (!obligations || obligations.length === 0) {
    return (
      <div className="empty-state-card" data-testid="empty-obligations">
        <p className="empty-title">No Obligations Extracted</p>
        <p className="empty-desc">
          No explicit contractual obligations or duties were identified.
        </p>
      </div>
    );
  }

  const parties = Array.from(new Set(obligations.map((o) => o.obligor))).sort();
  const filteredObligations =
    selectedParty === "ALL"
      ? obligations
      : obligations.filter((o) => o.obligor === selectedParty);

  return (
    <div className="workspace-panel" data-testid="obligations-view">
      <div className="panel-header">
        <h2 className="panel-title">
          Contractual Obligations ({obligations.length})
        </h2>
        <p className="panel-desc">
          Specific duties and compliance obligations extracted by party.
        </p>
      </div>

      <div
        className="category-filter-row"
        data-testid="obligation-party-filters"
      >
        <button
          type="button"
          className={`filter-chip ${selectedParty === "ALL" ? "active" : ""}`}
          onClick={() => setSelectedParty("ALL")}
          data-testid="filter-ob-all"
        >
          All Parties ({obligations.length})
        </button>
        {parties.map((party) => (
          <button
            key={party}
            type="button"
            className={`filter-chip ${selectedParty === party ? "active" : ""}`}
            onClick={() => setSelectedParty(party)}
            data-testid={`filter-ob-${party}`}
          >
            {party} ({obligations.filter((o) => o.obligor === party).length})
          </button>
        ))}
      </div>

      <div className="obligations-list">
        {filteredObligations.map((ob) => (
          <div
            key={ob.id}
            className="obligation-card"
            data-testid={`obligation-card-${ob.id}`}
          >
            <div className="obligation-header">
              <div className="obligor-badge">{ob.obligor}</div>
              <span className="badge-tier">DOCUMENT_FACT</span>
            </div>
            <p className="duty-text">{ob.duty}</p>
            {ob.trigger && (
              <div className="ob-meta-row">
                <span className="label">Trigger / Condition:</span>
                <span className="value">{ob.trigger}</span>
              </div>
            )}
            {ob.deadline && (
              <div className="ob-meta-row">
                <span className="label">Extracted Timing:</span>
                <span className="value font-semibold">{ob.deadline}</span>
              </div>
            )}
            <div className="card-source-row">
              <span className="source-page">
                {ob.page_start === ob.page_end
                  ? `Page ${ob.page_start}`
                  : `Pages ${ob.page_start}–${ob.page_end}`}
              </span>
              <button
                type="button"
                className="btn-inspect-sm"
                onClick={() =>
                  onInspect({
                    title: `${ob.obligor}'s Obligation`,
                    claimText: ob.duty,
                    claimType: "obligation",
                    pageStart: ob.page_start,
                    pageEnd: ob.page_end,
                    sourceSpan: ob.source_span || ob.duty,
                    trustTier: "DOCUMENT_FACT",
                  })
                }
                data-testid={`inspect-obligation-${ob.id}`}
                aria-label={`Inspect source for ${ob.obligor}'s obligation`}
              >
                Inspect Source
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
