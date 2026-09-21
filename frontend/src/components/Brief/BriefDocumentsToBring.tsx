import React from "react";

interface BriefDocumentsToBringProps {
  readonly documents: readonly string[];
}

export const BriefDocumentsToBring: React.FC<BriefDocumentsToBringProps> = ({
  documents,
}) => {
  if (!documents || documents.length === 0) {
    return null;
  }

  return (
    <div className="brief-section-card">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">
          Documents to Bring to Consultation
        </h3>
        <span className="brief-section-count">{documents.length} items</span>
      </div>
      <p className="brief-section-subtext">
        Prepare and attach these supplementary records to maximize attorney
        review efficiency:
      </p>

      <ul className="brief-checklist">
        {documents.map((doc, idx) => (
          <li key={`doc-${idx}`} className="brief-checklist-item">
            <span className="brief-doc-icon" aria-hidden="true">
              📄
            </span>
            <span className="brief-checklist-text">{doc}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
