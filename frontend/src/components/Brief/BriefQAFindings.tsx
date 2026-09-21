import React from "react";
import { BriefSection } from "../../types/brief";
import { InspectionTarget } from "../../types/workspace";

interface BriefQAFindingsProps {
  readonly qaSection?: BriefSection;
  readonly onInspect?: (target: InspectionTarget) => void;
}

export const BriefQAFindings: React.FC<BriefQAFindingsProps> = ({
  qaSection,
  onInspect,
}) => {
  if (!qaSection || !qaSection.items || qaSection.items.length === 0) {
    return null;
  }

  return (
    <div className="brief-section-card" data-testid="brief-qa-findings">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">Grounded Q&amp;A Findings</h3>
        <span className="brief-section-count">
          {qaSection.items.length} items
        </span>
      </div>
      <p className="brief-section-subtext">
        Verified answers and evidence citations from previous document
        inquiries:
      </p>

      <ul className="brief-questions-list">
        {qaSection.items.map((item, idx) => (
          <li key={item.id || `qa-item-${idx}`} className="brief-question-item">
            <div className="brief-question-content">
              {item.title && (
                <strong className="brief-item-title">{item.title}</strong>
              )}
              <p className="brief-question-text">{item.text || item.content}</p>
              {item.page_start !== undefined && (
                <span className="source-page-badge">
                  {item.page_start === item.page_end
                    ? `Page ${item.page_start}`
                    : `Pages ${item.page_start}–${item.page_end}`}
                </span>
              )}
            </div>

            {onInspect && (item.source_span || item.text) && (
              <button
                type="button"
                className="btn btn-inspect-link"
                onClick={() =>
                  onInspect({
                    title: item.title || "Q&A Finding",
                    claimText: item.text || item.content || "",
                    claimType: "grounded_qa",
                    pageStart: item.page_start,
                    pageEnd: item.page_end,
                    sourceSpan: item.source_span || item.text || "",
                    trustTier: item.trust_tier,
                  })
                }
                aria-label={`Inspect source for ${item.title || "Q&A Finding"}`}
              >
                Inspect Source
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
