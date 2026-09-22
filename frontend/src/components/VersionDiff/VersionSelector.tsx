import React from "react";
import { DocumentItem } from "../../types/document";
import { VersionDiffListItem } from "../../types/versionDiff";

interface VersionSelectorProps {
  readonly documents: readonly DocumentItem[];
  readonly pastDiffs: readonly VersionDiffListItem[];
  readonly selectedV1Id: string;
  readonly selectedV2Id: string;
  readonly onSelectV1: (id: string) => void;
  readonly onSelectV2: (id: string) => void;
  readonly onCompare: () => void;
  readonly onSelectPastDiff: (id: string) => void;
  readonly isComparing: boolean;
  readonly activeDiffId?: string;
}

export const VersionSelector: React.FC<VersionSelectorProps> = ({
  documents,
  pastDiffs,
  selectedV1Id,
  selectedV2Id,
  onSelectV1,
  onSelectV2,
  onCompare,
  onSelectPastDiff,
  isComparing,
  activeDiffId,
}) => {
  const readyDocs = documents.filter((d) => d.status === "READY");
  const canCompare =
    selectedV1Id &&
    selectedV2Id &&
    selectedV1Id !== selectedV2Id &&
    !isComparing;

  return (
    <section
      className="version-selector-container"
      aria-label="Document Version Selection"
    >
      <div className="version-selector-card">
        <h2 className="selector-title">Compare Document Versions</h2>
        <p className="selector-subtitle">
          Select two versions of the same legal document to view structured,
          evidence-grounded deltas.
        </p>

        <div className="version-dropdowns-row">
          <div className="version-select-group">
            <label htmlFor="version-1-select" className="version-label">
              <span className="version-tag base-tag">Version 1 (Base)</span>
            </label>
            <select
              id="version-1-select"
              className="version-dropdown"
              value={selectedV1Id}
              onChange={(e) => onSelectV1(e.target.value)}
              aria-label="Select Base Version 1"
            >
              <option value="">-- Select Base Version --</option>
              {readyDocs.map((doc) => (
                <option
                  key={`v1-${doc.id}`}
                  value={doc.id}
                  disabled={doc.id === selectedV2Id}
                >
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>

          <div className="version-swap-indicator" aria-hidden="true">
            &rarr;
          </div>

          <div className="version-select-group">
            <label htmlFor="version-2-select" className="version-label">
              <span className="version-tag revised-tag">
                Version 2 (Revised)
              </span>
            </label>
            <select
              id="version-2-select"
              className="version-dropdown"
              value={selectedV2Id}
              onChange={(e) => onSelectV2(e.target.value)}
              aria-label="Select Revised Version 2"
            >
              <option value="">-- Select Revised Version --</option>
              {readyDocs.map((doc) => (
                <option
                  key={`v2-${doc.id}`}
                  value={doc.id}
                  disabled={doc.id === selectedV1Id}
                >
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedV1Id && selectedV2Id && selectedV1Id === selectedV2Id && (
          <div className="version-error-banner" role="alert">
            Please select two different documents or versions to compare.
          </div>
        )}

        <div className="version-actions-row">
          <button
            type="button"
            className="btn btn-primary generate-diff-btn"
            onClick={onCompare}
            disabled={!canCompare}
            aria-busy={isComparing}
          >
            {isComparing ? "Generating Version Diff..." : "Compare Versions"}
          </button>
        </div>
      </div>

      {pastDiffs.length > 0 && (
        <div className="past-diffs-panel">
          <h3 className="past-diffs-heading">Saved Version Comparisons</h3>
          <ul className="past-diffs-list" role="list">
            {pastDiffs.map((diff) => {
              const isActive = diff.id === activeDiffId;
              return (
                <li key={diff.id} className="past-diff-item">
                  <button
                    type="button"
                    className={`past-diff-btn ${isActive ? "active" : ""}`}
                    onClick={() => onSelectPastDiff(diff.id)}
                    aria-current={isActive ? "true" : undefined}
                  >
                    <span className="diff-item-title">{diff.title}</span>
                    <span className="diff-item-meta">
                      {diff.v1_document?.filename} vs{" "}
                      {diff.v2_document?.filename} &bull;{" "}
                      {diff.summary?.total_findings ?? 0} findings
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
};
