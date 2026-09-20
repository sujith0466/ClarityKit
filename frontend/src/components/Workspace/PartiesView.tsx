import React from "react";
import { ExtractedParty } from "../../types/extraction";
import { InspectionTarget } from "../../types/workspace";

interface PartiesViewProps {
  parties: readonly ExtractedParty[];
  onInspect: (target: InspectionTarget) => void;
}

export const PartiesView: React.FC<PartiesViewProps> = ({
  parties,
  onInspect,
}) => {
  if (!parties || parties.length === 0) {
    return (
      <div className="empty-state-card" data-testid="empty-parties">
        <p className="empty-title">No Parties Identified</p>
        <p className="empty-desc">
          No distinct contracting entities were identified in this document.
        </p>
      </div>
    );
  }

  return (
    <div className="workspace-panel" data-testid="parties-view">
      <div className="panel-header">
        <h2 className="panel-title">Contracting Parties ({parties.length})</h2>
        <p className="panel-desc">
          Parties identified and extracted directly from document text.
        </p>
      </div>

      <div className="cards-grid">
        {parties.map((party) => (
          <div
            key={party.id}
            className="party-card"
            data-testid={`party-card-${party.id}`}
          >
            <div className="card-top-row">
              <h3 className="party-name">{party.name}</h3>
              <span className="badge-tier">DOCUMENT_FACT</span>
            </div>
            <div className="party-role-row">
              <span className="label">Role:</span>
              <span className="value font-semibold">
                {party.role || "Not specified"}
              </span>
            </div>
            <div className="card-source-row">
              <span className="source-page">Page {party.page_number}</span>
              <button
                type="button"
                className="btn-inspect-sm"
                onClick={() =>
                  onInspect({
                    title: party.name,
                    claimText: `${party.name} (Role: ${party.role || "party"})`,
                    claimType: "party",
                    pageNumber: party.page_number,
                    sourceSpan: party.source_span,
                    trustTier: "DOCUMENT_FACT",
                  })
                }
                data-testid={`inspect-party-${party.id}`}
                aria-label={`Inspect source for ${party.name}`}
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
