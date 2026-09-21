import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import { LawyerPreparationBrief } from "../../types/brief";
import { InspectionTarget } from "../../types/workspace";
import { BriefSafetyNotice } from "./BriefSafetyNotice";
import { BriefOverview } from "./BriefOverview";
import { BriefQuestions } from "./BriefQuestions";
import { BriefFactsToConfirm } from "./BriefFactsToConfirm";
import { BriefDocumentsToBring } from "./BriefDocumentsToBring";
import { BriefOpenQuestions } from "./BriefOpenQuestions";
import { BriefSnapshot } from "./BriefSnapshot";
import { BriefQAFindings } from "./BriefQAFindings";

interface LawyerBriefViewProps {
  readonly documentId: string;
  readonly documentFilename?: string;
  readonly onInspect?: (target: InspectionTarget) => void;
}

export const LawyerBriefView: React.FC<LawyerBriefViewProps> = ({
  documentId,
  documentFilename,
  onInspect,
}) => {
  const { token } = useAuth();
  const [brief, setBrief] = useState<LawyerPreparationBrief | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBrief = useCallback(async () => {
    if (!token || !documentId) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/documents/${documentId}/brief`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 404) {
        setBrief(null);
      } else if (res.ok) {
        const data = await res.json();
        setBrief(data.brief || data);
      } else {
        setError("Failed to load preparation brief.");
      }
    } catch {
      setError("Network error loading preparation brief.");
    } finally {
      setIsLoading(false);
    }
  }, [token, documentId]);

  useEffect(() => {
    fetchBrief();
  }, [fetchBrief]);

  const handleGenerate = async () => {
    if (!token || !documentId) return;

    setIsGenerating(true);
    setError(null);
    try {
      const res = await fetch(`/api/documents/${documentId}/brief`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (res.ok) {
        const data = await res.json();
        setBrief(data.brief || data);
      } else {
        const errData = await res.json().catch(() => null);
        setError(
          errData?.error || "Failed to generate lawyer-preparation brief."
        );
      }
    } catch {
      setError("Network error while assembling brief.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportPdf = async () => {
    if (!token || !brief) return;

    setIsExporting(true);
    try {
      const res = await fetch(`/api/briefs/${brief.id}/export/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement("a");
        link.href = url;
        const fname = documentFilename
          ? `brief_${documentFilename.replace(/\.[^/.]+$/, "")}.pdf`
          : `lawyer_brief_${brief.id.slice(0, 8)}.pdf`;
        link.download = fname;
        window.document.body.appendChild(link);
        link.click();
        window.document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } else {
        setError("Failed to export PDF.");
      }
    } catch {
      setError("Network error while exporting PDF.");
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="workspace-loading" data-testid="brief-loading">
        <div className="spinner" />
        <p>Loading Lawyer-Preparation Brief...</p>
      </div>
    );
  }

  if (!brief) {
    return (
      <div className="brief-empty-container" data-testid="brief-empty">
        <BriefSafetyNotice />
        <div className="empty-state-card">
          <h3 className="empty-title">No Lawyer Brief Generated Yet</h3>
          <p className="empty-desc">
            Assemble an evidence-grounded preparation brief compiling extracted
            terms, verified citations, strategic consultation questions, and
            document checklists.
          </p>
          {error && <p className="error-message">{error}</p>}
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={isGenerating}
            data-testid="generate-brief-btn"
          >
            {isGenerating
              ? "Assembling Brief..."
              : "Generate Lawyer-Preparation Brief"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="lawyer-brief-view" data-testid="lawyer-brief-view">
      <BriefSafetyNotice disclaimer={brief.disclaimer} />

      {error && <div className="error-banner">{error}</div>}

      <BriefOverview
        brief={brief}
        isGenerating={isGenerating}
        isExporting={isExporting}
        onGenerate={handleGenerate}
        onExportPdf={handleExportPdf}
      />

      <BriefQuestions
        questions={brief.questions_for_lawyer}
        onInspect={onInspect}
      />

      <div className="brief-two-col-grid">
        <BriefFactsToConfirm facts={brief.facts_to_confirm} />
        <BriefDocumentsToBring documents={brief.documents_to_bring} />
      </div>

      <BriefOpenQuestions questions={brief.open_questions} />

      <BriefSnapshot sections={brief.sections} onInspect={onInspect} />

      {brief.sections?.qa_findings && (
        <BriefQAFindings
          qaSection={brief.sections.qa_findings}
          onInspect={onInspect}
        />
      )}
    </div>
  );
};
