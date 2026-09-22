import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import { DocumentItem, DocumentPage } from "../../types/document";
import {
  DocumentVersionDiff,
  VersionDiffCategory,
  VersionDiffClassification,
  VersionDiffFinding,
  VersionDiffListItem,
  VersionEvidenceRef,
} from "../../types/versionDiff";
import { InspectionTarget } from "../../types/workspace";
import { VersionSelector } from "./VersionSelector";
import { VersionDiffOverview } from "./VersionDiffOverview";
import { SideBySideDiffCard } from "./SideBySideDiffCard";
import { UnifiedDiffCard } from "./UnifiedDiffCard";
import { SourceInspectorModal } from "../Workspace/SourceInspectorModal";

interface VersionDiffWorkspaceProps {
  readonly initialDiffId?: string;
}

export const VersionDiffWorkspace: React.FC<VersionDiffWorkspaceProps> = ({
  initialDiffId,
}) => {
  const { token } = useAuth();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [pastDiffs, setPastDiffs] = useState<VersionDiffListItem[]>([]);
  const [selectedV1Id, setSelectedV1Id] = useState<string>("");
  const [selectedV2Id, setSelectedV2Id] = useState<string>("");
  const [activeDiff, setActiveDiff] = useState<DocumentVersionDiff | null>(
    null
  );

  // Filters
  const [activeCategory, setActiveCategory] = useState<
    VersionDiffCategory | "ALL"
  >("ALL");
  const [activeClassification, setActiveClassification] = useState<
    VersionDiffClassification | "ALL"
  >("ALL");
  const [viewMode, setViewMode] = useState<"side-by-side" | "unified">(
    "side-by-side"
  );

  // States
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Source inspection
  const [inspectionTarget, setInspectionTarget] =
    useState<InspectionTarget | null>(null);
  const [inspectionPages, setInspectionPages] = useState<
    readonly DocumentPage[]
  >([]);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [docsRes, diffsRes] = await Promise.all([
        fetch("/api/documents", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch("/api/version-diffs", {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(docsData.documents || docsData || []);
      }
      if (diffsRes.ok) {
        const diffsData = await diffsRes.json();
        setPastDiffs(diffsData.version_diffs || diffsData || []);
      }
    } catch {
      setError("Failed to load documents or version diffs.");
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load initial diff if provided
  useEffect(() => {
    if (!initialDiffId || !token) return;
    const loadInitial = async () => {
      try {
        const res = await fetch(`/api/version-diffs/${initialDiffId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setActiveDiff(data.version_diff || data);
        }
      } catch {
        setError("Failed to load requested version diff.");
      }
    };
    loadInitial();
  }, [initialDiffId, token]);

  // Generate new diff
  const handleGenerateDiff = async () => {
    if (!selectedV1Id || !selectedV2Id || !token) return;
    setIsComparing(true);
    setError(null);

    try {
      const res = await fetch("/api/version-diffs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          v1_document_id: selectedV1Id,
          v2_document_id: selectedV2Id,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || "Failed to generate version diff.");
      }

      const data = await res.json();
      const newDiff: DocumentVersionDiff = data.version_diff || data;
      setActiveDiff(newDiff);
      // Refresh past diffs list
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Error generating version comparison.";
      setError(message);
    } finally {
      setIsComparing(false);
    }
  };

  // Load past diff
  const handleSelectPastDiff = async (diffId: string) => {
    if (!token) return;
    setError(null);
    try {
      const res = await fetch(`/api/version-diffs/${diffId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const diff: DocumentVersionDiff = data.version_diff || data;
        setActiveDiff(diff);
        setSelectedV1Id(diff.v1_document.id);
        setSelectedV2Id(diff.v2_document.id);
      }
    } catch {
      setError("Failed to load selected version diff.");
    }
  };

  // Source inspection modal trigger
  const handleInspectSource = async (
    ref: VersionEvidenceRef,
    finding: VersionDiffFinding
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
          title: `${finding.title} (${ref.version_label === "v1" ? "Base" : "Revised"})`,
          claimText: ref.exact_quote || ref.source_span,
          claimType: finding.category,
          pageStart: ref.page_start,
          pageEnd: ref.page_end,
          sourceSpan: ref.source_span,
          trustTier: ref.trust_tier,
          validationStatus: ref.validation_status,
        });
      }
    } catch {
      setError("Failed to load page text for citation inspection.");
    }
  };

  // Filter findings
  const filteredFindings = activeDiff
    ? activeDiff.findings.filter((f) => {
        const matchCategory =
          activeCategory === "ALL" || f.category === activeCategory;
        const matchClassification =
          activeClassification === "ALL" ||
          f.classification === activeClassification;
        return matchCategory && matchClassification;
      })
    : [];

  return (
    <div className="version-diff-workspace" aria-label="Version Diff Workspace">
      {/* Top Banner Alert */}
      {error && (
        <div className="diff-error-banner" role="alert">
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

      {/* Version Selector */}
      <VersionSelector
        documents={documents}
        pastDiffs={pastDiffs}
        selectedV1Id={selectedV1Id}
        selectedV2Id={selectedV2Id}
        onSelectV1={setSelectedV1Id}
        onSelectV2={setSelectedV2Id}
        onCompare={handleGenerateDiff}
        onSelectPastDiff={handleSelectPastDiff}
        isComparing={isComparing}
        activeDiffId={activeDiff?.id}
      />

      {/* Active Diff Display */}
      {activeDiff && (
        <main className="active-diff-container">
          <header className="active-diff-header">
            <h2 className="active-diff-title">{activeDiff.title}</h2>
            <div className="active-diff-versions-badge">
              <span className="badge-v1">
                Base: {activeDiff.v1_document.filename}
              </span>
              <span className="diff-vs-separator">vs</span>
              <span className="badge-v2">
                Revised: {activeDiff.v2_document.filename}
              </span>
            </div>
          </header>

          <VersionDiffOverview
            summary={activeDiff.summary}
            activeCategory={activeCategory}
            activeClassification={activeClassification}
            viewMode={viewMode}
            onSelectCategory={setActiveCategory}
            onSelectClassification={setActiveClassification}
            onToggleViewMode={setViewMode}
          />

          <div
            className="findings-stream"
            role="region"
            aria-label="Version Comparison Findings"
          >
            {filteredFindings.length > 0 ? (
              filteredFindings.map((finding) =>
                viewMode === "side-by-side" ? (
                  <SideBySideDiffCard
                    key={finding.id}
                    finding={finding}
                    v1Title={activeDiff.v1_document.filename}
                    v2Title={activeDiff.v2_document.filename}
                    onInspectSource={handleInspectSource}
                  />
                ) : (
                  <UnifiedDiffCard
                    key={finding.id}
                    finding={finding}
                    v1Title={activeDiff.v1_document.filename}
                    v2Title={activeDiff.v2_document.filename}
                    onInspectSource={handleInspectSource}
                  />
                )
              )
            ) : (
              <div className="no-findings-placeholder">
                <p>No findings matching the selected filters.</p>
              </div>
            )}
          </div>
        </main>
      )}

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
