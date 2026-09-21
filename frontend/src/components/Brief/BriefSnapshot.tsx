import React from "react";
import { BriefItem, BriefSection } from "../../types/brief";
import { InspectionTarget } from "../../types/workspace";

interface BriefSnapshotProps {
  readonly sections: Record<string, BriefSection>;
  readonly onInspect?: (target: InspectionTarget) => void;
}

export const BriefSnapshot: React.FC<BriefSnapshotProps> = ({
  sections,
  onInspect,
}) => {
  const sectionEntries = Object.entries(sections || {});

  if (sectionEntries.length === 0) {
    return null;
  }

  const renderItemSource = (item: BriefItem) => {
    if (item.page_start !== undefined && item.page_end !== undefined) {
      if (item.page_start === item.page_end) {
        return `Page ${item.page_start}`;
      }
      return `Pages ${item.page_start}–${item.page_end}`;
    }
    return null;
  };

  const getTierBadgeClass = (tier?: string) => {
    switch (tier) {
      case "DOCUMENT_FACT":
        return "badge-tier badge-fact";
      case "GENERAL_INFORMATION":
        return "badge-tier badge-info";
      case "INTERPRETATION":
        return "badge-tier badge-interp";
      case "PROFESSIONAL_REVIEW_NEEDED":
        return "badge-tier badge-review";
      default:
        return "badge-tier";
    }
  };

  return (
    <div className="brief-snapshot-container">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">
          Key Document Provisions &amp; Extracted Terms
        </h3>
        <span className="brief-section-count">
          {sectionEntries.length} sections
        </span>
      </div>
      <p className="brief-section-subtext">
        Evidence-grounded summary of parties, clauses, obligations, dates, and
        review areas:
      </p>

      <div className="brief-snapshot-sections">
        {sectionEntries.map(([key, section]) => {
          if (!section.items || section.items.length === 0) return null;

          return (
            <div
              key={key}
              className="brief-snapshot-section"
              data-testid={`brief-section-${key}`}
            >
              <div className="brief-snapshot-section-header">
                <h4 className="brief-snapshot-section-title">
                  {section.title}
                </h4>
                <span className="brief-snapshot-count">
                  ({section.items.length})
                </span>
              </div>
              {section.description && (
                <p className="brief-snapshot-desc">{section.description}</p>
              )}

              <ul className="brief-snapshot-item-list">
                {section.items.map((item, idx) => {
                  const sourcePageStr = renderItemSource(item);
                  return (
                    <li
                      key={item.id || `item-${key}-${idx}`}
                      className="brief-snapshot-item"
                    >
                      <div className="brief-snapshot-item-header">
                        {item.title && (
                          <strong className="brief-item-title">
                            {item.title}
                          </strong>
                        )}
                        <div className="brief-item-badges">
                          {item.trust_tier && (
                            <span
                              className={getTierBadgeClass(item.trust_tier)}
                            >
                              {item.trust_tier}
                            </span>
                          )}
                          {sourcePageStr && (
                            <span className="source-page-badge">
                              {sourcePageStr}
                            </span>
                          )}
                        </div>
                      </div>

                      <p className="brief-item-text">
                        {item.text || item.content}
                      </p>

                      {item.validation_reason && (
                        <p className="brief-item-reason">
                          <em>Note:</em> {item.validation_reason}
                        </p>
                      )}

                      {onInspect && (item.source_span || item.text) && (
                        <div className="brief-item-actions">
                          <button
                            type="button"
                            className="btn btn-inspect-link"
                            onClick={() =>
                              onInspect({
                                title: item.title || `${section.title} item`,
                                claimText: item.text || item.content || "",
                                claimType: item.source_type || key,
                                pageStart: item.page_start,
                                pageEnd: item.page_end,
                                sourceSpan: item.source_span || item.text || "",
                                trustTier: item.trust_tier,
                              })
                            }
                            aria-label={`Inspect source for ${item.title || section.title}`}
                          >
                            Inspect Source
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
};
