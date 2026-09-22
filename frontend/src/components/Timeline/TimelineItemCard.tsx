import React from "react";
import { TimelineEvidenceRef, TimelineItem } from "../../types/timeline";

interface TimelineItemCardProps {
  readonly item: TimelineItem;
  readonly onInspectSource: (
    ref: TimelineEvidenceRef,
    item: TimelineItem
  ) => void;
}

export const TimelineItemCard: React.FC<TimelineItemCardProps> = ({
  item,
  onInspectSource,
}) => {
  const getStatusBadge = () => {
    switch (item.item_status) {
      case "EXPLICIT_FACT":
        return (
          <span className="timeline-status-badge badge-explicit">
            Explicit Document Fact
          </span>
        );
      case "DERIVED":
        return (
          <span className="timeline-status-badge badge-derived">
            Derived Calculation
          </span>
        );
      case "UNRESOLVED_TRIGGER":
        return (
          <span className="timeline-status-badge badge-unresolved-trigger">
            Review Required (Missing Trigger)
          </span>
        );
      default:
        return null;
    }
  };

  const getDateDisplay = () => {
    if (item.calendar_date) {
      return (
        <time className="timeline-date-display" dateTime={item.calendar_date}>
          {item.calendar_date}
        </time>
      );
    }
    if (item.derived_date) {
      return (
        <time className="timeline-date-display" dateTime={item.derived_date}>
          {item.derived_date} (Derived)
        </time>
      );
    }
    return (
      <span className="timeline-date-display unspecified">
        {item.raw_date_text || "Unspecified Date"}
      </span>
    );
  };

  return (
    <article
      className={`timeline-item-card status-${item.item_status.toLowerCase()}`}
      aria-labelledby={`item-title-${item.id}`}
    >
      <div className="timeline-item-header">
        <div className="timeline-header-left">
          {getDateDisplay()}
          {getStatusBadge()}
        </div>
        <div className="timeline-header-right">
          <span className="timeline-date-type-tag">
            {item.date_type.replace("_", " ")}
          </span>
        </div>
      </div>

      <h3 id={`item-title-${item.id}`} className="timeline-item-title">
        {item.title}
      </h3>

      <div className="timeline-item-details">
        {item.party && (
          <p className="timeline-party">
            <strong>Party:</strong> {item.party}
          </p>
        )}
        <p className="timeline-duty">
          <strong>Event / Obligation:</strong> {item.duty_or_event}
        </p>
        <p className="timeline-raw-text">
          <strong>Stated in Document:</strong> "{item.raw_date_text}"
        </p>
      </div>

      {/* Derived Date Calculation Transparency Box */}
      {item.item_status === "DERIVED" && item.inputs_used.length > 0 && (
        <div
          className="derived-inputs-box"
          role="region"
          aria-label="Derived Calculation Inputs"
        >
          <h4 className="derived-inputs-heading">
            Mechanical Calculation Inputs:
          </h4>
          <ul className="derived-inputs-list">
            {item.inputs_used.map((input, idx) => (
              <li key={idx} className="derived-input-item">
                {input}
              </li>
            ))}
          </ul>
          <p className="derived-disclaimer">
            {item.notes ||
              "Calculated mechanically by calendar days. Legal or local business-day rules are not applied."}
          </p>
        </div>
      )}

      {/* Unresolved Trigger Alert */}
      {item.item_status === "UNRESOLVED_TRIGGER" && (
        <div
          className="unresolved-trigger-box"
          role="alert"
          aria-label="Missing Trigger Date Warning"
        >
          <h4 className="unresolved-heading">Missing Trigger Notice:</h4>
          <p className="unresolved-text">
            {item.notes ||
              "This relative deadline depends on an external or unstated trigger date. Please verify execution or delivery dates independently."}
          </p>
        </div>
      )}

      {/* Evidence Citations */}
      {item.evidence_references.length > 0 && (
        <div className="timeline-evidence-section">
          <h4 className="evidence-heading">Source Evidence:</h4>
          {item.evidence_references.map((ev, idx) => (
            <div key={idx} className="timeline-evidence-item">
              <blockquote className="timeline-quote">
                "{ev.exact_quote || ev.source_span}"
              </blockquote>
              <div className="timeline-evidence-footer">
                <span className="page-badge">
                  Page {ev.page_start}
                  {ev.page_end !== ev.page_start ? `–${ev.page_end}` : ""}
                </span>
                <button
                  type="button"
                  className="btn-inspect-source"
                  onClick={() => onInspectSource(ev, item)}
                  aria-label={`Inspect source text on page ${ev.page_start}`}
                >
                  Inspect Source
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
};
