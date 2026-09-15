import React, { useState } from "react";
import { DocumentUnderstanding } from "../../types/extraction";

interface DocumentUnderstandingViewProps {
  readonly understanding: DocumentUnderstanding;
  readonly documentFilename?: string;
  readonly onClose: () => void;
}

type ActiveTab = "parties" | "clauses" | "obligations" | "dates" | "flags";

export const DocumentUnderstandingView: React.FC<
  DocumentUnderstandingViewProps
> = ({ understanding, documentFilename, onClose }) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("parties");

  const {
    parties = [],
    clauses = [],
    obligations = [],
    dates = [],
    review_flags = [],
  } = understanding;

  return (
    <div
      className="understanding-view-container"
      data-testid="document-understanding-view"
    >
      <div className="understanding-header">
        <div className="understanding-title-area">
          <h3 className="understanding-title">
            Structured Understanding:{" "}
            {documentFilename || understanding.document_id}
          </h3>
          <span className="understanding-timestamp">
            Extracted: {new Date(understanding.extracted_at).toLocaleString()}
          </span>
        </div>
        <button
          type="button"
          className="understanding-close-btn"
          onClick={onClose}
          aria-label="Close structured understanding view"
        >
          &times; Close
        </button>
      </div>

      <div
        className="understanding-tablist"
        role="tablist"
        aria-label="Extraction Sections"
      >
        <button
          type="button"
          role="tab"
          id="tab-parties"
          aria-selected={activeTab === "parties"}
          aria-controls="panel-parties"
          className={`understanding-tab ${activeTab === "parties" ? "active" : ""}`}
          onClick={() => setActiveTab("parties")}
        >
          Parties <span className="tab-badge">{parties.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-clauses"
          aria-selected={activeTab === "clauses"}
          aria-controls="panel-clauses"
          className={`understanding-tab ${activeTab === "clauses" ? "active" : ""}`}
          onClick={() => setActiveTab("clauses")}
        >
          Clauses <span className="tab-badge">{clauses.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-obligations"
          aria-selected={activeTab === "obligations"}
          aria-controls="panel-obligations"
          className={`understanding-tab ${activeTab === "obligations" ? "active" : ""}`}
          onClick={() => setActiveTab("obligations")}
        >
          Obligations <span className="tab-badge">{obligations.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-dates"
          aria-selected={activeTab === "dates"}
          aria-controls="panel-dates"
          className={`understanding-tab ${activeTab === "dates" ? "active" : ""}`}
          onClick={() => setActiveTab("dates")}
        >
          Dates <span className="tab-badge">{dates.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-flags"
          aria-selected={activeTab === "flags"}
          aria-controls="panel-flags"
          className={`understanding-tab ${activeTab === "flags" ? "active" : ""}`}
          onClick={() => setActiveTab("flags")}
        >
          Review Flags <span className="tab-badge">{review_flags.length}</span>
        </button>
      </div>

      <div className="understanding-tab-content">
        {/* PARTIES PANEL */}
        {activeTab === "parties" && (
          <div
            id="panel-parties"
            role="tabpanel"
            aria-labelledby="tab-parties"
            className="understanding-panel"
          >
            {parties.length === 0 ? (
              <p className="empty-tab-text">
                No legal parties identified in document.
              </p>
            ) : (
              <div className="understanding-card-grid">
                {parties.map((party) => (
                  <div
                    key={party.id}
                    className="understanding-card"
                    data-testid={`party-card-${party.id}`}
                  >
                    <div className="card-header-row">
                      <h4 className="party-name">{party.name}</h4>
                      <span className="party-role-badge">{party.role}</span>
                    </div>
                    <div className="card-provenance-row">
                      <span className="page-citation">
                        Page {party.page_number}
                      </span>
                    </div>
                    {party.source_span && (
                      <blockquote className="card-source-span">
                        &ldquo;{party.source_span}&rdquo;
                      </blockquote>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CLAUSES PANEL */}
        {activeTab === "clauses" && (
          <div
            id="panel-clauses"
            role="tabpanel"
            aria-labelledby="tab-clauses"
            className="understanding-panel"
          >
            {clauses.length === 0 ? (
              <p className="empty-tab-text">No section clauses categorized.</p>
            ) : (
              <div className="understanding-card-grid">
                {clauses.map((clause) => (
                  <div
                    key={clause.id}
                    className="understanding-card"
                    data-testid={`clause-card-${clause.id}`}
                  >
                    <div className="card-header-row">
                      <h4 className="clause-title">
                        <span className="clause-ident">
                          {clause.clause_identifier}
                        </span>{" "}
                        {clause.title}
                      </h4>
                      <span className="clause-category-badge">
                        {clause.category}
                      </span>
                    </div>
                    <div className="card-provenance-row">
                      <span className="page-citation">
                        Page {clause.page_start}
                        {clause.page_end > clause.page_start
                          ? `–${clause.page_end}`
                          : ""}
                      </span>
                    </div>
                    <p className="clause-body-text">{clause.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* OBLIGATIONS PANEL */}
        {activeTab === "obligations" && (
          <div
            id="panel-obligations"
            role="tabpanel"
            aria-labelledby="tab-obligations"
            className="understanding-panel"
          >
            {obligations.length === 0 ? (
              <p className="empty-tab-text">
                No explicit duties or obligations extracted.
              </p>
            ) : (
              <div className="understanding-card-grid">
                {obligations.map((ob) => (
                  <div
                    key={ob.id}
                    className="understanding-card"
                    data-testid={`obligation-card-${ob.id}`}
                  >
                    <div className="card-header-row">
                      <span className="obligor-badge">{ob.obligor}</span>
                      {ob.deadline && (
                        <span className="obligation-deadline">
                          Due: {ob.deadline}
                        </span>
                      )}
                    </div>
                    <p className="obligation-duty">
                      <strong>Duty:</strong> {ob.duty}
                    </p>
                    {ob.trigger && (
                      <p className="obligation-trigger">
                        <strong>Condition:</strong> {ob.trigger}
                      </p>
                    )}
                    <div className="card-provenance-row">
                      <span className="page-citation">
                        Page {ob.page_start}
                        {ob.page_end > ob.page_start ? `–${ob.page_end}` : ""}
                      </span>
                    </div>
                    {ob.source_span && (
                      <blockquote className="card-source-span">
                        &ldquo;{ob.source_span}&rdquo;
                      </blockquote>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* DATES PANEL */}
        {activeTab === "dates" && (
          <div
            id="panel-dates"
            role="tabpanel"
            aria-labelledby="tab-dates"
            className="understanding-panel"
          >
            {dates.length === 0 ? (
              <p className="empty-tab-text">
                No contract dates or deadlines extracted.
              </p>
            ) : (
              <div className="understanding-card-grid">
                {dates.map((dt) => (
                  <div
                    key={dt.id}
                    className="understanding-card"
                    data-testid={`date-card-${dt.id}`}
                  >
                    <div className="card-header-row">
                      <h4 className="date-raw-text">{dt.raw_text}</h4>
                      <span className="date-type-badge">{dt.date_type}</span>
                    </div>
                    {dt.normalized_date && (
                      <span className="normalized-date-tag">
                        ISO: {dt.normalized_date}
                      </span>
                    )}
                    <p className="date-description">{dt.description}</p>
                    <div className="card-provenance-row">
                      <span className="page-citation">
                        Page {dt.page_number}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* REVIEW FLAGS PANEL */}
        {activeTab === "flags" && (
          <div
            id="panel-flags"
            role="tabpanel"
            aria-labelledby="tab-flags"
            className="understanding-panel"
          >
            <div className="flags-advisory-banner">
              <span className="advisory-icon" aria-hidden="true">
                &#9888;
              </span>
              <p>
                <strong>Advisory Overview:</strong> Review flags highlight terms
                that may warrant scrutiny or clarification. ClarityKit provides
                neutral structural extraction and does not offer legal advice.
              </p>
            </div>

            {review_flags.length === 0 ? (
              <p className="empty-tab-text">
                No notable advisory flags raised for this document.
              </p>
            ) : (
              <div className="understanding-card-grid">
                {review_flags.map((flag) => (
                  <div
                    key={flag.id}
                    className={`understanding-card flag-card flag-severity-${flag.severity}`}
                    data-testid={`flag-card-${flag.id}`}
                  >
                    <div className="card-header-row">
                      <h4 className="flag-title">{flag.title}</h4>
                      <span
                        className={`flag-severity-badge severity-${flag.severity}`}
                      >
                        {flag.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="flag-description">{flag.description}</p>
                    <div className="card-provenance-row">
                      <span className="page-citation">
                        Page {flag.page_start}
                        {flag.page_end > flag.page_start
                          ? `–${flag.page_end}`
                          : ""}
                      </span>
                    </div>
                    {flag.source_span && (
                      <blockquote className="card-source-span">
                        &ldquo;{flag.source_span}&rdquo;
                      </blockquote>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
