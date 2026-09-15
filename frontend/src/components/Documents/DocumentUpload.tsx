import React, { useState, useRef } from "react";
import { useAuth } from "../../context/useAuth";
import { DocumentItem, DocumentUploadResponse } from "../../types/document";

const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

interface DocumentUploadProps {
  onUploadSuccess?: (document: DocumentItem) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
}) => {
  const { token } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return "Invalid file type. Only PDF documents (.pdf) are supported.";
    }
    if (file.size === 0) {
      return "The selected file is empty (0 bytes).";
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const maxMb = MAX_FILE_SIZE_BYTES / (1024 * 1024);
      return `File size exceeds the maximum limit of ${maxMb} MB.`;
    }
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setErrorMessage(null);
    setSuccessMessage(null);

    if (file) {
      const error = validateFile(file);
      if (error) {
        setErrorMessage(error);
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    setErrorMessage(null);
    setSuccessMessage(null);

    const file = e.dataTransfer.files?.[0] || null;
    if (file) {
      const error = validateFile(file);
      if (error) {
        setErrorMessage(error);
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage("Please select a PDF document to upload.");
      return;
    }

    if (!token) {
      setErrorMessage("Authentication required to upload documents.");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/documents", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = (await response.json()) as DocumentUploadResponse & {
        message?: string;
        error?: string;
      };

      if (!response.ok) {
        setErrorMessage(data.message || "Failed to upload document.");
        setIsUploading(false);
        return;
      }

      setSuccessMessage(
        `Document "${data.document.filename}" uploaded successfully.`
      );
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      if (onUploadSuccess) {
        onUploadSuccess(data.document);
      }
    } catch {
      setErrorMessage("Network error during upload. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section
      className="card document-upload-card"
      aria-labelledby="upload-heading"
    >
      <h2 id="upload-heading">Upload Legal Document</h2>
      <p>
        Securely ingest contracts, leases, or agreements in PDF format for
        understanding.
      </p>

      {errorMessage && (
        <div
          className="auth-error-banner"
          role="alert"
          aria-live="assertive"
          data-testid="upload-error-banner"
        >
          {errorMessage}
        </div>
      )}

      {successMessage && (
        <div
          className="upload-success-banner"
          role="status"
          aria-live="polite"
          data-testid="upload-success-banner"
        >
          {successMessage}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="upload-form"
        aria-label="Document Upload Form"
      >
        <div
          className={`dropzone ${isDragging ? "dropzone-active" : ""}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          role="region"
          aria-label="Document Drop Zone"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
        >
          <input
            id="document-file-input"
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            style={{ display: "none" }}
            disabled={isUploading}
            aria-label="Select PDF file to upload"
          />
          <div className="dropzone-content">
            <div className="dropzone-icon" aria-hidden="true">
              📄
            </div>
            {selectedFile ? (
              <p className="dropzone-text">
                Selected: <strong>{selectedFile.name}</strong> (
                {(selectedFile.size / 1024).toFixed(1)} KB)
              </p>
            ) : (
              <p className="dropzone-text">
                Drag &amp; drop a PDF here, or <span>browse files</span>
              </p>
            )}
            <span className="dropzone-hint">
              Supported: PDF only (up to 20 MB)
            </span>
          </div>
        </div>

        <div className="upload-actions">
          <button
            type="submit"
            className="btn-primary"
            disabled={!selectedFile || isUploading}
            aria-busy={isUploading}
            data-testid="upload-submit-btn"
          >
            {isUploading ? "Uploading & Validating..." : "Upload Document"}
          </button>
        </div>
      </form>
    </section>
  );
};
