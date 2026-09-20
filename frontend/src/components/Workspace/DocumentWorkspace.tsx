import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import {
  DocumentItem,
  DocumentPage,
  DocumentPagesResponse,
} from "../../types/document";
import {
  DocumentUnderstanding,
  DocumentUnderstandingResponse,
} from "../../types/extraction";
import {
  DocumentEvidenceReport,
  DocumentEvidenceResponse,
} from "../../types/evidence";
import { DocumentTrustReport, TrustResponse } from "../../types/trust";
import { InspectionTarget, WorkspaceTab } from "../../types/workspace";
import { DocumentWorkspaceHeader } from "./DocumentWorkspaceHeader";
import { WorkspaceOverview } from "./WorkspaceOverview";
import { PartiesView } from "./PartiesView";
import { ClausesView } from "./ClausesView";
import { ObligationsView } from "./ObligationsView";
import { DatesView } from "./DatesView";
import { ReviewAreasView } from "./ReviewAreasView";
import { SourceInspectorModal } from "./SourceInspectorModal";
import { EvidenceViewer } from "../Documents/EvidenceViewer";
import { TrustSafetyViewer } from "../Documents/TrustSafetyViewer";

interface DocumentWorkspaceProps {
  documentId: string;
  initialDocument?: DocumentItem;
  onClose: () => void;
}

export const DocumentWorkspace: React.FC<DocumentWorkspaceProps> = ({
  documentId,
  initialDocument,
  onClose,
}) => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");
  const [document, setDocument] = useState<DocumentItem | null>(
    initialDocument || null
  );
  const [pages, setPages] = useState<readonly DocumentPage[]>([]);
  const [understanding, setUnderstanding] =
    useState<DocumentUnderstanding | null>(null);
  const [evidenceReport, setEvidenceReport] =
    useState<DocumentEvidenceReport | null>(null);
  const [trustReport, setTrustReport] = useState<DocumentTrustReport | null>(
    null
  );

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [inspectTarget, setInspectTarget] = useState<InspectionTarget | null>(
    null
  );

  const loadWorkspaceData = useCallback(async () => {
    if (!token || !documentId) return;

    setError(null);
    try {
      // 1. Load document metadata if not already available
      let currentDoc = document;
      if (!currentDoc) {
        const docRes = await fetch(`/api/documents/${documentId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (docRes.status === 404) {
          setError("The requested document was not found.");
          setIsLoading(false);
          return;
        }
        if (docRes.status === 401) {
          setError("Authentication required.");
          setIsLoading(false);
          return;
        }
        if (docRes.ok) {
          const docData = await docRes.json();
          currentDoc = docData.document;
          setDocument(currentDoc);
        }
      }

      // 2. Fetch pages, understanding, evidence, and trust in parallel
      const [pagesRes, underRes, evRes, trustRes] = await Promise.all([
        fetch(`/api/documents/${documentId}/pages`, {
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => null),
        fetch(`/api/documents/${documentId}/understanding`, {
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => null),
        fetch(`/api/documents/${documentId}/evidence`, {
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => null),
        fetch(`/api/documents/${documentId}/trust`, {
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => null),
      ]);

      if (pagesRes && pagesRes.ok) {
        const pData: DocumentPagesResponse = await pagesRes.json();
        setPages(pData.pages || []);
      }

      if (underRes && underRes.ok) {
        const uData: DocumentUnderstandingResponse = await underRes.json();
        setUnderstanding(uData.understanding);
      }

      if (evRes && evRes.ok) {
        const eData: DocumentEvidenceResponse = await evRes.json();
        setEvidenceReport(eData.evidence_report);
      }

      if (trustRes && trustRes.ok) {
        const tData: TrustResponse = await trustRes.json();
        setTrustReport(tData.trust_report);
      }
    } catch {
      setError("Network error while loading workspace data.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [token, documentId, document]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadWorkspaceData();
  };

  const tabs: { id: WorkspaceTab; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "parties", label: "Parties", count: understanding?.parties.length },
    { id: "clauses", label: "Clauses", count: understanding?.clauses.length },
    {
      id: "obligations",
      label: "Obligations",
      count: understanding?.obligations.length,
    },
    {
      id: "dates",
      label: "Important Dates",
      count: understanding?.dates.length,
    },
    {
      id: "review_areas",
      label: "Review Areas",
      count: understanding?.review_flags.length,
    },
    { id: "evidence", label: "Evidence" },
    { id: "trust", label: "Trust & Safety" },
  ];

  const handleKeyDownTabs = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const tabIds = tabs.map((t) => t.id);
    const currentIndex = tabIds.indexOf(activeTab);

    if (e.key === "ArrowRight") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % tabIds.length;
      setActiveTab(tabIds[nextIndex]);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + tabIds.length) % tabIds.length;
      setActiveTab(tabIds[prevIndex]);
    } else if (e.key === "Home") {
      e.preventDefault();
      setActiveTab(tabIds[0]);
    } else if (e.key === "End") {
      e.preventDefault();
      setActiveTab(tabIds[tabIds.length - 1]);
    }
  };

  if (isLoading) {
    return (
      <div
        className="workspace-loading"
        aria-busy="true"
        data-testid="workspace-loading"
      >
        <div className="spinner" />
        <p>Loading document understanding workspace...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="workspace-error-container" data-testid="workspace-error">
        <h2>Unable to load Document Workspace</h2>
        <p className="error-message">{error || "Document not found."}</p>
        <button type="button" className="btn-secondary" onClick={onClose}>
          Back to Documents
        </button>
      </div>
    );
  }

  return (
    <div className="document-workspace" data-testid="document-workspace">
      <DocumentWorkspaceHeader
        document={document}
        pageCount={pages.length}
        onBack={onClose}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      <nav
        className="workspace-tab-nav"
        role="tablist"
        aria-label="Document Understanding Views"
        onKeyDown={handleKeyDownTabs}
        data-testid="workspace-tablist"
      >
        {tabs.map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-controls={`panel-${tab.id}`}
              aria-selected={isSelected}
              tabIndex={isSelected ? 0 : -1}
              className={`workspace-tab-btn ${isSelected ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              data-testid={`workspace-tab-${tab.id}`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className="tab-count-badge">{tab.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      <main className="workspace-tab-content">
        {activeTab === "overview" && (
          <div
            role="tabpanel"
            id="panel-overview"
            aria-labelledby="tab-overview"
            tabIndex={0}
          >
            <WorkspaceOverview
              understanding={understanding}
              evidenceReport={evidenceReport}
              trustReport={trustReport}
              onSelectTab={setActiveTab}
            />
          </div>
        )}

        {activeTab === "parties" && (
          <div
            role="tabpanel"
            id="panel-parties"
            aria-labelledby="tab-parties"
            tabIndex={0}
          >
            <PartiesView
              parties={understanding?.parties || []}
              onInspect={setInspectTarget}
            />
          </div>
        )}

        {activeTab === "clauses" && (
          <div
            role="tabpanel"
            id="panel-clauses"
            aria-labelledby="tab-clauses"
            tabIndex={0}
          >
            <ClausesView
              clauses={understanding?.clauses || []}
              onInspect={setInspectTarget}
            />
          </div>
        )}

        {activeTab === "obligations" && (
          <div
            role="tabpanel"
            id="panel-obligations"
            aria-labelledby="tab-obligations"
            tabIndex={0}
          >
            <ObligationsView
              obligations={understanding?.obligations || []}
              onInspect={setInspectTarget}
            />
          </div>
        )}

        {activeTab === "dates" && (
          <div
            role="tabpanel"
            id="panel-dates"
            aria-labelledby="tab-dates"
            tabIndex={0}
          >
            <DatesView
              dates={understanding?.dates || []}
              onInspect={setInspectTarget}
            />
          </div>
        )}

        {activeTab === "review_areas" && (
          <div
            role="tabpanel"
            id="panel-review_areas"
            aria-labelledby="tab-review_areas"
            tabIndex={0}
          >
            <ReviewAreasView
              reviewFlags={understanding?.review_flags || []}
              onInspect={setInspectTarget}
            />
          </div>
        )}

        {activeTab === "evidence" && (
          <div
            role="tabpanel"
            id="panel-evidence"
            aria-labelledby="tab-evidence"
            tabIndex={0}
          >
            {evidenceReport ? (
              <EvidenceViewer
                report={evidenceReport}
                documentFilename={document.filename}
                onClose={() => setActiveTab("overview")}
              />
            ) : (
              <div
                className="empty-state-card"
                data-testid="empty-evidence-tab"
              >
                <p className="empty-title">No Evidence Report Available</p>
                <p className="empty-desc">
                  Evidence verification requires structured extraction to be
                  performed.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "trust" && (
          <div
            role="tabpanel"
            id="panel-trust"
            aria-labelledby="tab-trust"
            tabIndex={0}
          >
            {trustReport ? (
              <TrustSafetyViewer
                report={trustReport}
                documentFilename={document.filename}
                onClose={() => setActiveTab("overview")}
              />
            ) : (
              <div className="empty-state-card" data-testid="empty-trust-tab">
                <p className="empty-title">
                  No Trust &amp; Safety Report Available
                </p>
                <p className="empty-desc">
                  Trust assessment requires structured extraction and evidence
                  resolution.
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      {inspectTarget && (
        <SourceInspectorModal
          target={inspectTarget}
          pages={pages}
          onClose={() => setInspectTarget(null)}
        />
      )}
    </div>
  );
};
