import React from "react";
import {
  TimelineDateType,
  TimelineItemStatus,
  TimelineSummary,
} from "../../types/timeline";

interface TimelineOverviewProps {
  readonly summary: TimelineSummary;
  readonly activeStatus: TimelineItemStatus | "ALL";
  readonly activeDateType: TimelineDateType | "ALL";
  readonly onSelectStatus: (status: TimelineItemStatus | "ALL") => void;
  readonly onSelectDateType: (dt: TimelineDateType | "ALL") => void;
}

export const TimelineOverview: React.FC<TimelineOverviewProps> = ({
  summary,
  activeStatus,
  activeDateType,
  onSelectStatus,
  onSelectDateType,
}) => {
  const statusFilters: {
    id: TimelineItemStatus | "ALL";
    label: string;
    count: number;
  }[] = [
    { id: "ALL", label: "All Items", count: summary.total_items },
    {
      id: "EXPLICIT_FACT",
      label: "Explicit Document Facts",
      count: summary.fixed_date_count + summary.duration_count,
    },
    {
      id: "DERIVED",
      label: "Derived Calculations",
      count: summary.derived_count,
    },
    {
      id: "UNRESOLVED_TRIGGER",
      label: "Unresolved Triggers",
      count: summary.unresolved_trigger_count,
    },
  ];

  const dateTypeFilters: (TimelineDateType | "ALL")[] = [
    "ALL",
    "FIXED_DATE",
    "RELATIVE_DEADLINE",
    "DURATION",
    "UNSPECIFIED",
  ];

  return (
    <section className="timeline-overview" aria-label="Timeline Overview">
      {/* Metric summary boxes */}
      <div className="timeline-metrics-grid">
        <div className="metric-box total">
          <span className="metric-num">{summary.total_items}</span>
          <span className="metric-label">Total Milestones</span>
        </div>
        <div className="metric-box fixed">
          <span className="metric-num">{summary.fixed_date_count}</span>
          <span className="metric-label">Fixed Dates</span>
        </div>
        <div className="metric-box derived">
          <span className="metric-num">{summary.derived_count}</span>
          <span className="metric-label">Derived Dates</span>
        </div>
        <div className="metric-box unresolved">
          <span className="metric-num">{summary.unresolved_trigger_count}</span>
          <span className="metric-label">Unresolved Triggers</span>
        </div>
        <div className="metric-box duration">
          <span className="metric-num">{summary.duration_count}</span>
          <span className="metric-label">Durations</span>
        </div>
      </div>

      {/* Filter controls */}
      <div className="timeline-controls-bar">
        <div
          className="status-filters"
          role="group"
          aria-label="Filter by item status"
        >
          {statusFilters.map((st) => (
            <button
              key={st.id}
              type="button"
              className={`filter-pill ${activeStatus === st.id ? "active" : ""}`}
              onClick={() => onSelectStatus(st.id)}
              aria-pressed={activeStatus === st.id}
            >
              {st.label} ({st.count})
            </button>
          ))}
        </div>

        <div
          className="date-type-filters"
          role="group"
          aria-label="Filter by date type"
        >
          <span className="date-type-label">Date Types:</span>
          {dateTypeFilters.map((dt) => (
            <button
              key={dt}
              type="button"
              className={`cat-pill ${activeDateType === dt ? "active" : ""}`}
              onClick={() => onSelectDateType(dt)}
              aria-pressed={activeDateType === dt}
            >
              {dt.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
};
