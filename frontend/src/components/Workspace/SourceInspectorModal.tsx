import React, { useEffect, useRef } from "react";
import { DocumentPage } from "../../types/document";
import { InspectionTarget } from "../../types/workspace";

interface SourceInspectorModalProps {
  target: InspectionTarget;
  pages: readonly DocumentPage[];
  onClose: () => void;
}

export const SourceInspectorModal: React.FC<SourceInspectorModalProps> = ({
  target,
  pages,
  onClose,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const pageNum = target.pageNumber || target.pageStart || 1;
  const pageRecord = pages.find((p) => p.page_number === pageNum);

  useEffect(() => {
    closeBtnRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const renderHighlightedPageText = (fullText: string, span: string) => {
    if (!fullText || !span) {
      return <span>{fullText || "No page text available."}</span>;
    }

    const lowerFull = fullText.toLowerCase();
    const lowerSpan = span.trim().toLowerCase();
    const matchIndex = lowerFull.indexOf(lowerSpan);

    if (matchIndex === -1) {
      return (
        <div>
          <div className="source-span-box">
            <strong>Cited Span:</strong> &ldquo;{span}&rdquo;
          </div>
          <p className="page-full-text">{fullText}</p>
        </div>
      );
    }

    const before = fullText.slice(0, matchIndex);
    const match = fullText.slice(matchIndex, matchIndex + span.trim().length);
    const after = fullText.slice(matchIndex + span.trim().length);

    return (
      <p className="page-full-text">
        <span>{before}</span>
        <mark className="source-highlight" data-testid="source-highlight-text">
          {match}
        </mark>
        <span>{after}</span>
      </p>
    );
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="source-inspector-title"
      data-testid="source-inspector-modal"
    >
      <div className="modal-container source-inspector-dialog" ref={modalRef}>
        <div className="modal-header">
          <div>
            <h2 id="source-inspector-title" className="modal-title">
              Source Citation &amp; Evidence
            </h2>
            <span className="modal-subtitle">
              Authoritative Page {pageNum} Context
            </span>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            ref={closeBtnRef}
            aria-label="Close source inspection dialog"
            data-testid="close-source-inspector"
          >
            &times;
          </button>
        </div>

        <div className="modal-body">
          <div className="source-metadata-card">
            <div className="source-meta-item">
              <span className="label">Claim Item:</span>
              <span className="value font-bold">{target.title}</span>
            </div>
            <div className="source-meta-item">
              <span className="label">Claim Type:</span>
              <span className="value uppercase">{target.claimType}</span>
            </div>
            {target.trustTier && (
              <div className="source-meta-item">
                <span className="label">Trust Tier:</span>
                <span className="badge-tier">{target.trustTier}</span>
              </div>
            )}
            <div className="source-meta-item">
              <span className="label">Authoritative Page:</span>
              <span className="value">Page {pageNum}</span>
            </div>
          </div>

          <div className="source-text-section">
            <h3 className="section-subtitle">
              Authoritative Document Page Text
            </h3>
            <div
              className="page-text-container"
              data-testid="authoritative-page-text"
            >
              {pageRecord
                ? renderHighlightedPageText(pageRecord.text, target.sourceSpan)
                : renderHighlightedPageText("", target.sourceSpan)}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <span className="disclaimer-mini">
            Source resolved against authoritative DocumentPage text.
          </span>
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            data-testid="modal-done-btn"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
