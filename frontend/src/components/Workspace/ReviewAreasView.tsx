import React from "react";
import { ExtractedReviewFlag } from "../../types/extraction";
import { InspectionTarget } from "../../types/workspace";

interface ReviewAreasViewProps {
  reviewFlags: readonly ExtractedReviewFlag[];
  onInspect: (target: InspectionTarget) => void;
}

export const ReviewAreasView: React.FC<ReviewAreasViewProps> = ({
  reviewFlags,
  onInspect,
}) => {
  if (!reviewFlags || reviewFlags.length === 0) {
    return (
      <div className="empty-state-card" data-testid="empty-review-areas">
        <p className="empty-title">No Review Areas Flagged</p>
        <p className="empty-desc">
          No review areas were identified by the current analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="workspace-panel" data-testid="review-areas-view">
      <div className="panel-header">
        <h2 className="panel-title">Review Areas ({reviewFlags.length})</h2>
        <p className="panel-desc">
          Items flagged for closer attention or professional review.
        </p>
      </div>

      <div className="review-flags-list">
        {reviewFlags.map((flag) => (
          <div
            key={flag.id}
            className={`review-flag-card severity-${flag.severity}`}
            data-testid={`review-flag-card-${flag.id}`}
          >
            <div className="flag-top-row">
              <div className="flag-title-group">
                <h3 className="flag-title">{flag.title}</h3>
                <span className={`badge-severity ${flag.severity}`}>
                  {flag.severity.toUpperCase()} ATTENTION
                </span>
                <span className="badge-flag-type">{flag.flag_type}</span>
              </div>
              <span className="badge-tier review">
                PROFESSIONAL_REVIEW_NEEDED
              </span>
            </div>

            <p className="flag-desc">{flag.description}</p>

            <div className="professional-review-box">
              <strong>Professional Review Needed:</strong> This item may require
              additional facts, jurisdiction-specific analysis, or review by a
              qualified legal professional.
            </div>

            <div className="card-source-row">
              <span className="source-page">
                {flag.page_start === flag.page_end
                  ? `Page ${flag.page_start}`
                  : `Pages ${flag.page_start}–${flag.page_end}`}
              </span>
              <button
                type="button"
                className="btn-inspect-sm"
                onClick={() =>
                  onInspect({
                    title: flag.title,
                    claimText: flag.description,
                    claimType: "review_flag",
                    pageStart: flag.page_start,
                    pageEnd: flag.page_end,
                    sourceSpan: flag.source_span || flag.description,
                    trustTier: "PROFESSIONAL_REVIEW_NEEDED",
                  })
                }
                data-testid={`inspect-review-flag-${flag.id}`}
                aria-label={`Inspect source for ${flag.title}`}
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
