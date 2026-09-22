import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import { DocumentItem, DocumentPage } from "../../types/document";
import {
  DocumentTimeline,
  TimelineDateType,
  TimelineEvidenceRef,
  TimelineItem,
  TimelineItemStatus,
} from "../../types/timeline";
import { InspectionTarget } from "../../types/workspace";
import { TimelineOverview } from "./TimelineOverview";
import { TimelineItemCard } from "./TimelineItemCard";
import { SourceInspectorModal } from "../Workspace/SourceInspectorModal";

interface TimelineWorkspaceProps {
  readonly initialDocumentId?: string;
}

export const TimelineWorkspace: React.FC<TimelineWorkspaceProps> = ({
  initialDocumentId,
}) => {
  const { token } = useAuth();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(
    initialDocumentId || ""
  );
  const [activeTimeline, setActiveTimeline] = useState<DocumentTimeline | null>(
    null
  );

  // Filter state
  const [activeStatus, setActiveStatus] = useState<TimelineItemStatus | "ALL">(
    "ALL"
  );
  const [activeDateType, setActiveDateType] = useState<
    TimelineDateType | "ALL"
  >("ALL");

  // Loading & error states
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Source inspection modal
  const [inspectionTarget, setInspectionTarget] =
    useState<InspectionTarget | null>(null);
  const [inspectionPages, setInspectionPages] = useState<
    readonly DocumentPage[]
  >([]);

  // Fetch documents
  const fetchData = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const docsRes = await fetch("/api/documents", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(docsData.documents || docsData || []);
      }
    } catch {
      setError("Failed to load documents.");
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load timeline for selected document if already exists
  const loadTimelineForDoc = useCallback(
    async (docId: string) => {
      if (!docId || !token) return;
      setError(null);
      try {
        const res = await fetch(`/api/documents/${docId}/timeline`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setActiveTimeline(data.timeline || data);
        } else if (res.status === 404) {
          // Not generated yet
          setActiveTimeline(null);
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.message || "Failed to load timeline.");
        }
      } catch {
        setError("Error connecting to timeline service.");
      }
    },
    [token]
  );

  useEffect(() => {
    if (selectedDocId) {
      loadTimelineForDoc(selectedDocId);
    }
  }, [selectedDocId, loadTimelineForDoc]);

  // Generate timeline
  const handleGenerateTimeline = async () => {
    if (!selectedDocId || !token) return;
    setIsGenerating(true);
    setError(null);

    try {
      const res = await fetch(`/api/documents/${selectedDocId}/timeline`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || "Failed to generate timeline.");
      }

      const data = await res.json();
      setActiveTimeline(data.timeline || data);
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Error generating document timeline.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  // Inspect source trigger
  const handleInspectSource = async (
    ref: TimelineEvidenceRef,
    item: TimelineItem
  ) => {
    if (!token) return;
    try {
      const res = await fetch(`/api/documents/${ref.document_id}/pages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const pagesData = await res.json();
        setInspectionPages(pagesData.pages || pagesData || []);
        setInspectionTarget({
          title: item.title,
          claimText: item.duty_or_event || item.title,
          claimType: item.date_type,
          pageStart: ref.page_start,
          pageEnd: ref.page_end,
          sourceSpan: ref.source_span,
          trustTier: item.trust_tier,
          validationStatus: ref.validation_status,
        });
      }
    } catch {
      setError("Failed to load page text for citation inspection.");
    }
  };

  const readyDocs = documents.filter((d) => d.status === "READY");
  const filteredItems = activeTimeline
    ? activeTimeline.items.filter((item) => {
        const matchStatus =
          activeStatus === "ALL" || item.item_status === activeStatus;
        const matchDateType =
          activeDateType === "ALL" || item.date_type === activeDateType;
        return matchStatus && matchDateType;
      })
    : [];

  return (
    <div className="timeline-workspace" aria-label="Timeline Workspace">
      {/* Error Banner */}
      {error && (
        <div className="timeline-error-banner" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="btn-dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}

      {/* Document Selector Card */}
      <section
        className="timeline-doc-selector-card"
        aria-label="Select Document for Timeline"
      >
        <h2 className="timeline-title">Deadline &amp; Obligation Timeline</h2>
        <p className="timeline-subtitle">
          Construct an evidence-grounded chronological timeline of contractual
          milestones, explicit dates, and mechanically derived deadlines.
        </p>

        <div className="timeline-selector-row">
          <div className="select-wrapper">
            <label htmlFor="timeline-doc-select" className="doc-select-label">
              Select Document:
            </label>
            <select
              id="timeline-doc-select"
              className="timeline-doc-dropdown"
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              aria-label="Select a document to generate timeline"
            >
              <option value="">-- Choose a document --</option>
              {readyDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="btn btn-primary generate-timeline-btn"
            onClick={handleGenerateTimeline}
            disabled={!selectedDocId || isGenerating}
            aria-busy={isGenerating}
          >
            {isGenerating
              ? "Generating Timeline..."
              : activeTimeline
                ? "Regenerate Timeline"
                : "Generate Timeline"}
          </button>
        </div>
      </section>

      {/* Active Timeline View */}
      {activeTimeline ? (
        <main className="active-timeline-container">
          <header className="active-timeline-header">
            <h3 className="active-timeline-title">{activeTimeline.title}</h3>
            <span className="doc-badge">
              Document: {activeTimeline.document_title}
            </span>
          </header>

          <TimelineOverview
            summary={activeTimeline.summary}
            activeStatus={activeStatus}
            activeDateType={activeDateType}
            onSelectStatus={setActiveStatus}
            onSelectDateType={setActiveDateType}
          />

          <div
            className="timeline-stream"
            role="feed"
            aria-label="Chronological Timeline Items"
          >
            {filteredItems.length > 0 ? (
              filteredItems.map((item) => (
                <TimelineItemCard
                  key={item.id}
                  item={item}
                  onInspectSource={handleInspectSource}
                />
              ))
            ) : (
              <div className="no-items-placeholder">
                <p>No timeline items matching the selected filters.</p>
              </div>
            )}
          </div>
        </main>
      ) : selectedDocId && !isGenerating ? (
        <div className="timeline-empty-state">
          <p>
            No timeline generated yet for this document. Click "Generate
            Timeline" to create one.
          </p>
        </div>
      ) : null}

      {/* Source Inspector Modal */}
      {inspectionTarget && (
        <SourceInspectorModal
          target={inspectionTarget}
          pages={inspectionPages}
          onClose={() => setInspectionTarget(null)}
        />
      )}
    </div>
  );
};
