import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import { DocumentItem, DocumentPage } from "../../types/document";
import {
  ComparisonCategory,
  ComparisonListItem,
  DifferenceClassification,
  DocumentComparison,
} from "../../types/comparison";
import { InspectionTarget } from "../../types/workspace";
import { ComparisonSelector } from "./ComparisonSelector";
import { ComparisonOverview } from "./ComparisonOverview";
import { SideBySideFindingCard } from "./SideBySideFindingCard";
import { SourceInspectorModal } from "../Workspace/SourceInspectorModal";

interface ComparisonWorkspaceProps {
  readonly initialComparisonId?: string;
}

export const ComparisonWorkspace: React.FC<ComparisonWorkspaceProps> = ({
  initialComparisonId,
}) => {
  const { token } = useAuth();

  // Documents & comparisons state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [comparisons, setComparisons] = useState<ComparisonListItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [activeComparison, setActiveComparison] =
    useState<DocumentComparison | null>(null);

  // Filter state
  const [activeCategory, setActiveCategory] = useState<
    ComparisonCategory | "ALL"
  >("ALL");
  const [activeClassification, setActiveClassification] = useState<
    DifferenceClassification | "ALL"
  >("ALL");

  // Loading and error states
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [isLoadingComparison, setIsLoadingComparison] =
    useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Source Inspection modal state
  const [inspectionTarget, setInspectionTarget] =
    useState<InspectionTarget | null>(null);
  const [inspectionPages, setInspectionPages] = useState<
    readonly DocumentPage[]
  >([]);

  // Fetch documents and comparisons
  const fetchData = useCallback(async () => {
    if (!token) return;
    setIsLoadingList(true);
    setError(null);
    try {
      const [docsRes, compsRes] = await Promise.all([
        fetch("/api/documents", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch("/api/comparisons", {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(docsData.documents || docsData || []);
      }
      if (compsRes.ok) {
        const compsData = await compsRes.json();
        setComparisons(compsData.comparisons || compsData || []);
      }
    } catch {
      setError("Failed to load documents or comparisons.");
    } finally {
      setIsLoadingList(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load initial comparison if provided
  useEffect(() => {
    if (!initialComparisonId || !token) return;
    const loadInitial = async () => {
      setIsLoadingComparison(true);
      try {
        const res = await fetch(`/api/comparisons/${initialComparisonId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setActiveComparison(data.comparison || data);
        }
      } catch {
        setError("Failed to load initial comparison.");
      } finally {
        setIsLoadingComparison(false);
      }
    };
    loadInitial();
  }, [initialComparisonId, token]);

  // Handle creating a new comparison
  const handleCreateComparison = async (title?: string) => {
    if (!token || selectedDocIds.length < 2 || selectedDocIds.length > 5)
      return;

    setIsComparing(true);
    setError(null);
    try {
      const res = await fetch("/api/comparisons", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_ids: selectedDocIds,
          title: title || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const newComparison: DocumentComparison = data.comparison || data;
        setActiveComparison(newComparison);
        fetchData();
      } else {
        const errData = await res.json().catch(() => null);
        setError(
          errData?.error?.message ||
            errData?.message ||
            "Failed to generate comparison."
        );
      }
    } catch {
      setError("Network error while generating comparison.");
    } finally {
      setIsComparing(false);
    }
  };

  // Handle viewing an existing comparison
  const handleSelectComparison = async (id: string) => {
    if (!token) return;
    setIsLoadingComparison(true);
    setError(null);
    try {
      const res = await fetch(`/api/comparisons/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveComparison(data.comparison || data);
      } else {
        setError("Failed to fetch comparison details.");
      }
    } catch {
      setError("Network error loading comparison.");
    } finally {
      setIsLoadingComparison(false);
    }
  };

  // Handle deleting a comparison
  const handleDeleteComparison = async (id: string) => {
    if (
      !token ||
      !window.confirm("Are you sure you want to delete this comparison?")
    )
      return;

    try {
      const res = await fetch(`/api/comparisons/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        if (activeComparison?.id === id) {
          setActiveComparison(null);
        }
        fetchData();
      } else {
        setError("Failed to delete comparison.");
      }
    } catch {
      setError("Network error deleting comparison.");
    }
  };

  // Handle inspection of evidence source
  const handleInspect = async (target: InspectionTarget, docId?: string) => {
    if (!token) return;
    setInspectionTarget(target);
    const targetDocId = docId || activeComparison?.documents[0]?.id;
    if (targetDocId) {
      try {
        const res = await fetch(`/api/documents/${targetDocId}/pages`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setInspectionPages(data.pages || data || []);
        }
      } catch {
        setInspectionPages([]);
      }
    }
  };

  // Filtered findings
  const filteredFindings = (activeComparison?.findings || []).filter((f) => {
    if (activeCategory !== "ALL" && f.category !== activeCategory) return false;
    if (
      activeClassification !== "ALL" &&
      f.classification !== activeClassification
    )
      return false;
    return true;
  });

  return (
    <div
      className="comparison-workspace-container"
      data-testid="comparison-workspace"
    >
      {/* Header / Navigation Bar */}
      <div className="comparison-workspace-header">
        <div className="header-left">
          <h1 className="workspace-title">Multi-Document Comparison</h1>
          {activeComparison && (
            <span className="active-comparison-badge">
              {activeComparison.title} ({activeComparison.documents.length}{" "}
              Documents)
            </span>
          )}
        </div>
        <div className="header-actions">
          {activeComparison && (
            <>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setActiveComparison(null)}
              >
                ← Back to Selector & History
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleDeleteComparison(activeComparison.id)}
              >
                Delete Comparison
              </button>
            </>
          )}
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {/* Main Content Area */}
      {activeComparison ? (
        /* Active Comparison View */
        <div className="active-comparison-view">
          <ComparisonOverview
            summary={activeComparison.summary}
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
            activeClassification={activeClassification}
            onClassificationChange={setActiveClassification}
            disclaimer={activeComparison.disclaimer}
          />

          <div
            className="comparison-findings-list"
            role="feed"
            aria-label="Comparison Findings"
          >
            <div className="findings-count-header">
              <h3>
                Findings ({filteredFindings.length} of{" "}
                {activeComparison.findings.length})
              </h3>
            </div>

            {filteredFindings.length === 0 ? (
              <div className="empty-findings-state">
                <p>
                  No findings match the selected category and classification
                  filters.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setActiveCategory("ALL");
                    setActiveClassification("ALL");
                  }}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              filteredFindings.map((finding) => (
                <SideBySideFindingCard
                  key={finding.id}
                  finding={finding}
                  documents={activeComparison.documents}
                  onInspect={(target) => {
                    // Find document id matching evidence
                    const matchingDocId = Object.entries(
                      finding.evidence_by_doc
                    ).find(
                      ([, ev]) => ev.exact_quote === target.claimText
                    )?.[0];
                    handleInspect(target, matchingDocId);
                  }}
                />
              ))
            )}
          </div>
        </div>
      ) : (
        /* Selector & History View */
        <div className="comparison-dashboard-grid">
          <div className="dashboard-column-main">
            <ComparisonSelector
              documents={documents}
              selectedDocIds={selectedDocIds}
              onSelectionChange={setSelectedDocIds}
              onCompare={handleCreateComparison}
              isComparing={isComparing}
              error={error}
            />
          </div>

          <div className="dashboard-column-sidebar">
            <div className="comparison-history-card">
              <h3>Saved Comparisons ({comparisons.length})</h3>
              {isLoadingList ? (
                <p className="loading-text">Loading comparison history...</p>
              ) : comparisons.length === 0 ? (
                <p className="no-history-text">
                  No previous comparisons found.
                </p>
              ) : (
                <ul className="comparison-history-list">
                  {comparisons.map((c) => (
                    <li key={c.id} className="comparison-history-item">
                      <button
                        type="button"
                        className="history-item-btn"
                        onClick={() => handleSelectComparison(c.id)}
                        disabled={isLoadingComparison}
                      >
                        <div className="history-item-title">{c.title}</div>
                        <div className="history-item-meta">
                          {c.document_count} docs •{" "}
                          {new Date(c.created_at).toLocaleDateString()}
                        </div>
                        <div className="history-item-summary">
                          <span className="badge badge-success">
                            {c.summary.total_matches} matches
                          </span>
                          <span className="badge badge-warning">
                            {c.summary.total_inconsistencies} inconsistencies
                          </span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
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
