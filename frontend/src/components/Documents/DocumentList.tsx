import React, { useState } from "react";
import { DocumentItem } from "../../types/document";

interface DocumentListProps {
  documents: readonly DocumentItem[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onDeleteDocument: (documentId: string) => Promise<void>;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  isLoading,
  error,
  onRefresh,
  onDeleteDocument,
}) => {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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
    } finally {
      setDeletingId(null);
    }
  };

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
                <tr key={doc.id} data-testid={`document-row-${doc.id}`}>
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
                      className={`status-badge status-${doc.status}`}
                      data-testid={`status-badge-${doc.id}`}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td>{formatDate(doc.created_at)}</td>
                  <td>
                    {confirmDeleteId === doc.id ? (
                      <div className="confirm-actions">
                        <button
                          type="button"
                          className="btn-danger-confirm"
                          onClick={() => handleDelete(doc.id)}
                          disabled={deletingId === doc.id}
                          aria-label={`Confirm delete ${doc.filename}`}
                        >
                          {deletingId === doc.id ? "Deleting..." : "Confirm"}
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
