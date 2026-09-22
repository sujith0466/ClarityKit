import React, { useState } from "react";
import { DocumentItem } from "../../types/document";

interface ComparisonSelectorProps {
  readonly documents: readonly DocumentItem[];
  readonly selectedDocIds: readonly string[];
  readonly onSelectionChange: (docIds: string[]) => void;
  readonly onCompare: (title?: string) => void;
  readonly isComparing: boolean;
  readonly error?: string | null;
}

export const ComparisonSelector: React.FC<ComparisonSelectorProps> = ({
  documents,
  selectedDocIds,
  onSelectionChange,
  onCompare,
  isComparing,
  error,
}) => {
  const [title, setTitle] = useState<string>("");

  // Filter ready documents
  const readyDocs = documents.filter((d) => d.status === "READY");

  const handleToggle = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      onSelectionChange(selectedDocIds.filter((id) => id !== docId));
    } else {
      if (selectedDocIds.length >= 5) return;
      onSelectionChange([...selectedDocIds, docId]);
    }
  };

  const isValidSelection =
    selectedDocIds.length >= 2 && selectedDocIds.length <= 5;

  return (
    <div className="comparison-selector-card" data-testid="comparison-selector">
      <div className="comparison-selector-header">
        <h2 className="comparison-selector-title">Multi-Document Comparison</h2>
        <p className="comparison-selector-subtitle">
          Select between 2 and 5 processed documents to compare parties, dates,
          notice periods, clauses, and potential inconsistencies.
        </p>
      </div>

      <div className="comparison-selector-title-input">
        <label htmlFor="comparison-title-field" className="form-label">
          Comparison Title (Optional):
        </label>
        <input
          id="comparison-title-field"
          type="text"
          className="form-input"
          placeholder="e.g. Master Lease vs 2026 Addendum"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isComparing}
        />
      </div>

      <div
        className="comparison-document-list"
        role="group"
        aria-label="Select documents to compare"
      >
        <div className="comparison-doc-list-header">
          <span>Available Documents ({readyDocs.length})</span>
          <span className="selection-count-badge">
            {selectedDocIds.length} of 5 selected (min 2)
          </span>
        </div>

        {readyDocs.length === 0 ? (
          <p className="no-documents-message">
            No ready documents available. Please upload and process documents
            first.
          </p>
        ) : (
          <ul className="comparison-doc-items">
            {readyDocs.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <li
                  key={doc.id}
                  className={`comparison-doc-item ${isSelected ? "selected" : ""}`}
                >
                  <label className="comparison-doc-label">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggle(doc.id)}
                      disabled={
                        isComparing ||
                        (!isSelected && selectedDocIds.length >= 5)
                      }
                      aria-label={`Select ${doc.filename}`}
                    />
                    <div className="comparison-doc-info">
                      <span className="doc-filename">{doc.filename}</span>
                      <span className="doc-meta">
                        {(doc.size_bytes / 1024).toFixed(1)} KB •{" "}
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {error && (
        <div className="comparison-error-banner" role="alert">
          {error}
        </div>
      )}

      <div className="comparison-actions">
        <button
          type="button"
          className="btn btn-primary btn-compare"
          disabled={!isValidSelection || isComparing}
          onClick={() => onCompare(title.trim() || undefined)}
          aria-busy={isComparing}
        >
          {isComparing
            ? "Analyzing Documents..."
            : `Compare ${selectedDocIds.length} Documents`}
        </button>
      </div>
    </div>
  );
};
