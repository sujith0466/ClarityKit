import React from "react";
import { DocumentItem } from "../../types/document";

interface DocumentWorkspaceHeaderProps {
  document: DocumentItem;
  pageCount?: number;
  onBack: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const DocumentWorkspaceHeader: React.FC<
  DocumentWorkspaceHeaderProps
> = ({ document, pageCount, onBack, onRefresh, isRefreshing = false }) => {
  const statusClass = `status-badge status-${document.status.toLowerCase()}`;
  const formattedSize =
    document.size_bytes > 1024 * 1024
      ? `${(document.size_bytes / (1024 * 1024)).toFixed(1)} MB`
      : `${Math.round(document.size_bytes / 1024)} KB`;

  return (
    <header className="workspace-header" data-testid="workspace-header">
      <div className="workspace-header-top">
        <button
          type="button"
          className="btn-back"
          onClick={onBack}
          aria-label="Back to documents list"
          data-testid="workspace-back-btn"
        >
          &larr; Documents
        </button>
        <div className="workspace-header-actions">
          {onRefresh && (
            <button
              type="button"
              className="btn-refresh"
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label="Refresh document data"
              data-testid="workspace-refresh-btn"
            >
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button>
          )}
        </div>
      </div>

      <div className="workspace-header-main">
        <div className="workspace-title-area">
          <h1
            className="workspace-document-title"
            data-testid="workspace-doc-title"
          >
            {document.filename}
          </h1>
          <div className="workspace-metadata-row">
            <span className={statusClass} data-testid="workspace-status-badge">
              {document.status.toUpperCase()}
            </span>
            {pageCount !== undefined && pageCount > 0 && (
              <span className="meta-badge" data-testid="workspace-page-count">
                {pageCount} {pageCount === 1 ? "Page" : "Pages"}
              </span>
            )}
            <span className="meta-badge">{formattedSize}</span>
            <span className="meta-date">
              Uploaded on {new Date(document.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
