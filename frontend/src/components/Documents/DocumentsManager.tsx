import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/useAuth";
import { DocumentItem, DocumentListResponse } from "../../types/document";
import {
  DocumentUnderstanding,
  DocumentUnderstandingResponse,
} from "../../types/extraction";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentList } from "./DocumentList";
import { RetrievalSearch } from "./RetrievalSearch";
import { DocumentUnderstandingView } from "./DocumentUnderstandingView";

export const DocumentsManager: React.FC = () => {
  const { token, isAuthenticated } = useAuth();
  const [documents, setDocuments] = useState<readonly DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeUnderstanding, setActiveUnderstanding] =
    useState<DocumentUnderstanding | null>(null);
  const [activeDocFilename, setActiveDocFilename] = useState<string>("");

  const fetchDocuments = useCallback(async () => {
    if (!token || !isAuthenticated) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/documents", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = (await response.json()) as DocumentListResponse & {
        message?: string;
      };

      if (!response.ok) {
        setError(data.message || "Failed to fetch documents.");
        return;
      }

      setDocuments(data.documents);
    } catch {
      setError("Network error while fetching documents.");
    } finally {
      setIsLoading(false);
    }
  }, [token, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchDocuments();
    } else {
      setDocuments([]);
    }
  }, [isAuthenticated, token, fetchDocuments]);

  const handleUploadSuccess = (newDoc: DocumentItem) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!token) return;

    try {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.message || "Failed to delete document.");
        return;
      }

      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      if (activeUnderstanding?.document_id === documentId) {
        setActiveUnderstanding(null);
        setActiveDocFilename("");
      }
    } catch {
      setError("Network error while deleting document.");
    }
  };

  const handleProcessDocument = async (documentId: string) => {
    if (!token) return;

    try {
      const response = await fetch(`/api/documents/${documentId}/process`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.message || "Failed to process document.");
        return;
      }

      // Update document status locally to READY
      setDocuments((prev) =>
        prev.map((doc) =>
          doc.id === documentId ? { ...doc, status: "ready" as const } : doc
        )
      );
    } catch {
      setError("Network error while triggering document processing.");
    }
  };

  const handleIndexDocument = async (documentId: string) => {
    if (!token) return;

    try {
      const response = await fetch(`/api/documents/${documentId}/index`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.message || "Failed to index document.");
        return;
      }
    } catch {
      setError("Network error while indexing document.");
    }
  };

  const handleExtractDocument = async (documentId: string) => {
    if (!token) return;

    setError(null);
    try {
      const response = await fetch(`/api/documents/${documentId}/extract`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      const data = (await response.json()) as DocumentUnderstandingResponse & {
        message?: string;
      };

      if (!response.ok) {
        setError(data.message || "Structured extraction failed.");
        return;
      }

      const doc = documents.find((d) => d.id === documentId);
      setActiveDocFilename(doc?.filename || documentId);
      setActiveUnderstanding(data.understanding);
    } catch {
      setError("Network error while extracting document understanding.");
    }
  };

  const handleViewUnderstanding = async (
    documentId: string,
    filename: string
  ) => {
    if (!token) return;

    setError(null);
    try {
      const response = await fetch(
        `/api/documents/${documentId}/understanding`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = (await response.json()) as DocumentUnderstandingResponse & {
        message?: string;
      };

      if (!response.ok) {
        setError(
          data.message ||
            "No structured understanding found. Please run 'Extract' first."
        );
        return;
      }

      setActiveDocFilename(filename);
      setActiveUnderstanding(data.understanding);
    } catch {
      setError("Network error while fetching document understanding.");
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="documents-section" data-testid="documents-manager">
      <DocumentUpload onUploadSuccess={handleUploadSuccess} />
      <DocumentList
        documents={documents}
        isLoading={isLoading}
        error={error}
        onRefresh={fetchDocuments}
        onDeleteDocument={handleDeleteDocument}
        onProcessDocument={handleProcessDocument}
        onIndexDocument={handleIndexDocument}
        onExtractDocument={handleExtractDocument}
        onViewUnderstanding={handleViewUnderstanding}
      />
      {activeUnderstanding && (
        <DocumentUnderstandingView
          understanding={activeUnderstanding}
          documentFilename={activeDocFilename}
          onClose={() => {
            setActiveUnderstanding(null);
            setActiveDocFilename("");
          }}
        />
      )}
      <RetrievalSearch />
    </div>
  );
};
