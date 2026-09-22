import React from "react";
import { LawyerPreparationBrief } from "../../types/brief";

interface BriefOverviewProps {
  readonly brief: LawyerPreparationBrief;
  readonly isGenerating: boolean;
  readonly isExporting: boolean;
  readonly onGenerate: () => void;
  readonly onExportPdf: () => void;
}

export const BriefOverview: React.FC<BriefOverviewProps> = ({
  brief,
  isGenerating,
  isExporting,
  onGenerate,
  onExportPdf,
}) => {
  const completenessPct = Math.round(brief.completeness_score * 100);

  return (
    <div className="brief-overview-card">
      <div className="brief-overview-header">
        <div className="brief-overview-meta">
          <h2 className="brief-title">{brief.title}</h2>
          <div className="brief-meta-details">
            <span className="brief-meta-item">
              Generated: {new Date(brief.created_at).toLocaleDateString()}
            </span>
            <span className="brief-meta-item">
              Document ID: <code>{(brief.document_id || "").slice(0, 8)}</code>
            </span>
          </div>
        </div>
        <div className="brief-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onGenerate}
            disabled={isGenerating}
            aria-label="Refresh lawyer preparation brief"
          >
            {isGenerating ? "Assembling Brief..." : "Refresh Brief"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onExportPdf}
            disabled={isExporting}
            aria-label="Export lawyer preparation brief as PDF"
          >
            {isExporting ? "Exporting PDF..." : "Export PDF"}
          </button>
        </div>
      </div>

      <div className="brief-completeness-container">
        <div className="brief-completeness-label">
          <span>Brief Completeness Score</span>
          <strong>{completenessPct}%</strong>
        </div>
        <div
          className="brief-completeness-bar"
          role="progressbar"
          aria-label="Brief completeness score"
          aria-valuenow={completenessPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuetext={`${completenessPct}% complete`}
        >
          <div
            className="brief-completeness-fill"
            style={{ width: `${completenessPct}%` }}
          />
        </div>
      </div>

      {brief.situation_summary && (
        <div className="brief-summary-box">
          <h3 className="brief-section-heading">Executive Summary</h3>
          <p className="brief-summary-text">{brief.situation_summary}</p>
        </div>
      )}
    </div>
  );
};
