import React, { useState } from "react";
import { DocumentItem, DocumentPage } from "../../types/document";
import { useAuth } from "../../context/useAuth";

interface DocumentListProps {
  documents: readonly DocumentItem[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onDeleteDocument: (documentId: string) => Promise<void>;
  onProcessDocument?: (documentId: string) => Promise<void>;
  onIndexDocument?: (documentId: string) => Promise<void>;
  onExtractDocument?: (documentId: string) => Promise<void>;
  onViewUnderstanding?: (documentId: string, filename: string) => Promise<void>;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  isLoading,
  error,
  onRefresh,
  onDeleteDocument,
  onProcessDocument,
  onIndexDocument,
  onExtractDocument,
  onViewUnderstanding,
}) => {
  const { token } = useAuth();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [indexingId, setIndexingId] = useState<string | null>(null);
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [pagesLoading, setPagesLoading] = useState<boolean>(false);
  const [docPages, setDocPages] = useState<readonly DocumentPage[]>([]);
  const [pagesError, setPagesError] = useState<string | null>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDeleteDocument(id);
      setConfirmDeleteId(null);
      if (expandedDocId === id) {
        setExpandedDocId(null);
        setDocPages([]);
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleProcess = async (id: string) => {
    if (!onProcessDocument) return;
    setProcessingId(id);
    try {
      await onProcessDocument(id);
    } finally {
      setProcessingId(null);
    }
  };

  const handleIndex = async (id: string) => {
    if (!onIndexDocument) return;
    setIndexingId(id);
    try {
      await onIndexDocument(id);
    } finally {
      setIndexingId(null);
    }
  };

  const handleExtract = async (id: string) => {
    if (!onExtractDocument) return;
    setExtractingId(id);
    try {
      await onExtractDocument(id);
    } finally {
      setExtractingId(null);
    }
  };

  const handleTogglePages = async (docId: string) => {
    if (expandedDocId === docId) {
      setExpandedDocId(null);
      setDocPages([]);
      setPagesError(null);
      return;
    }

    setExpandedDocId(docId);
    setPagesLoading(true);
    setPagesError(null);

    try {
      const res = await fetch(`/api/documents/${docId}/pages`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const data = await res.json();
        setPagesError(data.message || "Failed to load document pages.");
        setDocPages([]);
        return;
      }

      const data = await res.json();
      setDocPages(data.pages || []);
    } catch {
      setPagesError("Network error while retrieving pages.");
      setDocPages([]);
    } finally {
      setPagesLoading(false);
    }
  };

  const isReady = (status: string) => status.toLowerCase() === "ready";
  const isProcessable = (status: string) =>
    ["queued", "failed"].includes(status.toLowerCase());
  const isProcessing = (status: string, id: string) =>
    status.toLowerCase() === "processing" || processingId === id;
  const isIndexing = (id: string) => indexingId === id;

  return (
    <section
      className="card document-list-card"
      aria-labelledby="documents-heading"
    >
      <div className="document-list-header">
        <div>
          <h2 id="documents-heading">Your Legal Documents</h2>
          <p>Managed documents stored securely under your account.</p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={onRefresh}
          disabled={isLoading}
          aria-label="Refresh document list"
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          className="auth-error-banner"
          role="alert"
          aria-live="assertive"
          data-testid="list-error-banner"
        >
          {error}
        </div>
      )}

      {isLoading && documents.length === 0 ? (
        <div className="loading-state" data-testid="documents-loading">
          <p>Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="empty-state" data-testid="documents-empty">
          <p>No legal documents uploaded yet.</p>
          <span>
            Upload a PDF contract, lease, or agreement above to get started.
          </span>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="documents-table" aria-label="Uploaded Documents">
            <thead>
              <tr>
                <th scope="col">Document</th>
                <th scope="col">Size</th>
                <th scope="col">Status</th>
                <th scope="col">Uploaded</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <React.Fragment key={doc.id}>
                  <tr data-testid={`document-row-${doc.id}`}>
                    <td>
                      <div className="doc-name-cell">
                        <span className="doc-icon" aria-hidden="true">
                          📄
                        </span>
                        <strong className="doc-filename">{doc.filename}</strong>
                      </div>
                    </td>
                    <td>{formatFileSize(doc.size_bytes)}</td>
                    <td>
                      <span
                        className={`status-badge status-${doc.status.toLowerCase()}`}
                        data-testid={`status-badge-${doc.id}`}
                      >
                        {isProcessing(doc.status, doc.id)
                          ? "PROCESSING"
                          : doc.status.toUpperCase()}
                      </span>
                    </td>
                    <td>{formatDate(doc.created_at)}</td>
                    <td>
                      <div className="table-row-actions">
                        {isProcessable(doc.status) && (
                          <button
                            type="button"
                            className="btn-primary-sm"
                            onClick={() => handleProcess(doc.id)}
                            disabled={isProcessing(doc.status, doc.id)}
                            data-testid={`process-btn-${doc.id}`}
                            aria-label={`Process document ${doc.filename}`}
                          >
                            {isProcessing(doc.status, doc.id)
                              ? "Processing..."
                              : "Process"}
                          </button>
                        )}

                        {isReady(doc.status) && (
                          <>
                            <button
                              type="button"
                              className="btn-primary-sm"
                              onClick={() => handleIndex(doc.id)}
                              disabled={isIndexing(doc.id)}
                              data-testid={`index-btn-${doc.id}`}
                              aria-label={`Index document ${doc.filename}`}
                            >
                              {isIndexing(doc.id) ? "Indexing..." : "Index"}
                            </button>
                            {onExtractDocument && (
                              <button
                                type="button"
                                className="btn-primary-sm btn-extract"
                                onClick={() => handleExtract(doc.id)}
                                disabled={extractingId === doc.id}
                                data-testid={`extract-btn-${doc.id}`}
                                aria-label={`Extract understanding for ${doc.filename}`}
                              >
                                {extractingId === doc.id
                                  ? "Extracting..."
                                  : "Extract"}
                              </button>
                            )}
                            {onViewUnderstanding && (
                              <button
                                type="button"
                                className="btn-secondary-sm"
                                onClick={() =>
                                  onViewUnderstanding(doc.id, doc.filename)
                                }
                                data-testid={`view-understanding-btn-${doc.id}`}
                                aria-label={`View understanding for ${doc.filename}`}
                              >
                                Understanding
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn-secondary-sm"
                              onClick={() => handleTogglePages(doc.id)}
                              data-testid={`view-pages-btn-${doc.id}`}
                              aria-label={`View extracted pages for ${doc.filename}`}
                            >
                              {expandedDocId === doc.id
                                ? "Hide Pages"
                                : "View Pages"}
                            </button>
                          </>
                        )}

                        {confirmDeleteId === doc.id ? (
                          <div className="confirm-actions">
                            <button
                              type="button"
                              className="btn-danger-confirm"
                              onClick={() => handleDelete(doc.id)}
                              disabled={deletingId === doc.id}
                              aria-label={`Confirm delete ${doc.filename}`}
                            >
                              {deletingId === doc.id
                                ? "Deleting..."
                                : "Confirm"}
                            </button>
                            <button
                              type="button"
                              className="btn-cancel"
                              onClick={() => setConfirmDeleteId(null)}
                              disabled={deletingId === doc.id}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn-delete"
                            onClick={() => setConfirmDeleteId(doc.id)}
                            disabled={deletingId === doc.id}
                            aria-label={`Delete ${doc.filename}`}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>

                  {expandedDocId === doc.id && (
                    <tr
                      className="expanded-pages-row"
                      data-testid={`pages-panel-${doc.id}`}
                    >
                      <td colSpan={5}>
                        <div className="pages-inspection-container">
                          <h4>
                            Extracted Pages for <em>{doc.filename}</em>
                          </h4>
                          {pagesLoading ? (
                            <p data-testid="pages-loading">
                              Loading extracted pages...
                            </p>
                          ) : pagesError ? (
                            <div
                              className="auth-error-banner"
                              data-testid="pages-error"
                            >
                              {pagesError}
                            </div>
                          ) : docPages.length === 0 ? (
                            <p data-testid="pages-empty">
                              No pages extracted for this document.
                            </p>
                          ) : (
                            <div
                              className="pages-list"
                              data-testid="pages-grid"
                            >
                              {docPages.map((page) => (
                                <div
                                  key={page.page_id}
                                  className="page-item-card"
                                  data-testid={`page-card-${page.page_number}`}
                                >
                                  <div className="page-item-header">
                                    <span className="page-number-tag">
                                      Page {page.page_number}
                                    </span>
                                    <span
                                      className={`method-badge method-${page.extraction_method.toLowerCase()}`}
                                      data-testid={`page-method-${page.page_number}`}
                                    >
                                      {page.extraction_method.toUpperCase()}
                                    </span>
                                    <span className="page-meta-counts">
                                      {page.word_count} words |{" "}
                                      {page.char_count} chars
                                    </span>
                                  </div>
                                  <div className="page-text-preview">
                                    <pre>{page.text}</pre>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
