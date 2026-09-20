import React from "react";
import { ExtractedDate } from "../../types/extraction";
import { InspectionTarget } from "../../types/workspace";

interface DatesViewProps {
  dates: readonly ExtractedDate[];
  onInspect: (target: InspectionTarget) => void;
}

export const DatesView: React.FC<DatesViewProps> = ({ dates, onInspect }) => {
  if (!dates || dates.length === 0) {
    return (
      <div className="empty-state-card" data-testid="empty-dates">
        <p className="empty-title">No Important Dates Identified</p>
        <p className="empty-desc">
          No contractual dates or deadlines were identified in this document.
        </p>
      </div>
    );
  }

  return (
    <div className="workspace-panel" data-testid="dates-view">
      <div className="panel-header">
        <h2 className="panel-title">Important Dates ({dates.length})</h2>
        <p className="panel-desc">
          Extracted dates, deadlines, and timeframes with source citations.
        </p>
      </div>

      <div className="cards-grid">
        {dates.map((dt) => (
          <div
            key={dt.id}
            className="date-card"
            data-testid={`date-card-${dt.id}`}
          >
            <div className="date-card-top">
              <span className="date-raw-text">{dt.raw_text}</span>
              <span className="badge-category">{dt.date_type}</span>
            </div>
            {dt.normalized_date && (
              <div className="date-normalized-row">
                <span className="label">Normalized (ISO):</span>
                <span className="value font-mono">{dt.normalized_date}</span>
              </div>
            )}
            <p className="date-desc">
              {dt.description || "Contractual date reference"}
            </p>
            <div className="card-source-row">
              <span className="source-page">Page {dt.page_number}</span>
              <button
                type="button"
                className="btn-inspect-sm"
                onClick={() =>
                  onInspect({
                    title: `Date: ${dt.raw_text}`,
                    claimText: `${dt.raw_text} (${dt.description || dt.date_type})`,
                    claimType: "date",
                    pageNumber: dt.page_number,
                    sourceSpan: dt.source_span || dt.raw_text,
                    trustTier: "DOCUMENT_FACT",
                  })
                }
                data-testid={`inspect-date-${dt.id}`}
                aria-label={`Inspect source for date ${dt.raw_text}`}
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
