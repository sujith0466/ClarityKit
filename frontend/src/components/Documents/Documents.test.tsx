import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentList } from "./DocumentList";
import { DocumentsManager } from "./DocumentsManager";
import { AuthContext, AuthContextType } from "../../context/AuthContext";
import { DocumentItem } from "../../types/document";

const sampleDocument: DocumentItem = {
  id: "doc-uuid-1234",
  filename: "lease_agreement.pdf",
  size_bytes: 1048576, // 1 MB
  content_type: "application/pdf",
  sha256_hash: "a1b2c3d4e5f6",
  status: "ready",
  created_at: "2026-09-15T10:00:00Z",
  updated_at: "2026-09-15T10:00:00Z",
};

const sampleUser = {
  user_id: "user-uuid-9999",
  email: "test@example.com",
  name: "Test User",
  is_active: true,
  created_at: "2026-09-15T10:00:00Z",
  updated_at: "2026-09-15T10:00:00Z",
};

const renderWithAuth = (
  ui: React.ReactElement,
  authOverrides?: Partial<AuthContextType>
) => {
  const defaultAuth: AuthContextType = {
    user: sampleUser,
    token: "valid-mock-jwt",
    isAuthenticated: true,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    setError: vi.fn(),
    ...authOverrides,
  };

  return render(
    <AuthContext.Provider value={defaultAuth}>{ui}</AuthContext.Provider>
  );
};

describe("DocumentUpload Component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders upload area and controls", () => {
    renderWithAuth(<DocumentUpload />);

    expect(
      screen.getByRole("heading", { name: /upload legal document/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload document/i })
    ).toBeDisabled();
    expect(screen.getByText(/supported: pdf only/i)).toBeInTheDocument();
  });

  it("rejects non-PDF files on client-side validation", async () => {
    renderWithAuth(<DocumentUpload />);

    const fileInput = screen.getByLabelText(/select pdf file to upload/i);
    const nonPdfFile = new File(["fake content"], "contract.docx", {
      type: "application/vnd.openxmlformats",
    });

    fireEvent.change(fileInput, { target: { files: [nonPdfFile] } });

    expect(
      await screen.findByText(
        /invalid file type\. only pdf documents \(\.pdf\) are supported\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload document/i })
    ).toBeDisabled();
  });

  it("rejects empty (0 byte) files", async () => {
    renderWithAuth(<DocumentUpload />);

    const fileInput = screen.getByLabelText(/select pdf file to upload/i);
    const emptyFile = new File([], "empty.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [emptyFile] } });

    expect(
      await screen.findByText(/the selected file is empty/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload document/i })
    ).toBeDisabled();
  });

  it("rejects files exceeding 20 MB", async () => {
    renderWithAuth(<DocumentUpload />);

    const fileInput = screen.getByLabelText(/select pdf file to upload/i);
    const largeContent = new Uint8Array(21 * 1024 * 1024);
    const largeFile = new File([largeContent], "large.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(fileInput, { target: { files: [largeFile] } });

    expect(
      await screen.findByText(/file size exceeds the maximum limit of 20 MB/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload document/i })
    ).toBeDisabled();
  });

  it("uploads valid PDF successfully when authenticated", async () => {
    const onUploadSuccess = vi.fn();
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "success", document: sampleDocument }),
    });
    globalThis.fetch = mockFetch;

    renderWithAuth(<DocumentUpload onUploadSuccess={onUploadSuccess} />);

    const fileInput = screen.getByLabelText(/select pdf file to upload/i);
    const validPdf = new File(
      ["%PDF-1.4 sample content"],
      "lease_agreement.pdf",
      { type: "application/pdf" }
    );

    fireEvent.change(fileInput, { target: { files: [validPdf] } });

    const submitBtn = screen.getByRole("button", { name: /upload document/i });
    expect(submitBtn).toBeEnabled();

    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/documents",
        expect.objectContaining({
          method: "POST",
          headers: { Authorization: "Bearer valid-mock-jwt" },
        })
      );
    });

    expect(
      await screen.findByText(
        /document "lease_agreement\.pdf" uploaded successfully\./i
      )
    ).toBeInTheDocument();
    expect(onUploadSuccess).toHaveBeenCalledWith(sampleDocument);
  });
});

describe("DocumentList Component", () => {
  it("renders empty state when documents list is empty", () => {
    renderWithAuth(
      <DocumentList
        documents={[]}
        isLoading={false}
        error={null}
        onRefresh={vi.fn()}
        onDeleteDocument={vi.fn()}
      />
    );

    expect(
      screen.getByText(/no legal documents uploaded yet/i)
    ).toBeInTheDocument();
  });

  it("renders document items with metadata and status badges", () => {
    renderWithAuth(
      <DocumentList
        documents={[sampleDocument]}
        isLoading={false}
        error={null}
        onRefresh={vi.fn()}
        onDeleteDocument={vi.fn()}
      />
    );

    expect(screen.getByText("lease_agreement.pdf")).toBeInTheDocument();
    expect(screen.getByText("1.0 MB")).toBeInTheDocument();
    expect(screen.getByTestId("status-badge-doc-uuid-1234")).toHaveTextContent(
      "READY"
    );
  });

  it("handles confirmation before deleting document", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);

    renderWithAuth(
      <DocumentList
        documents={[sampleDocument]}
        isLoading={false}
        error={null}
        onRefresh={vi.fn()}
        onDeleteDocument={onDelete}
      />
    );

    const deleteBtn = screen.getByRole("button", {
      name: /delete lease_agreement\.pdf/i,
    });
    await userEvent.click(deleteBtn);

    // Confirmation button appears
    const confirmBtn = screen.getByRole("button", {
      name: /confirm delete lease_agreement\.pdf/i,
    });
    expect(confirmBtn).toBeInTheDocument();

    await userEvent.click(confirmBtn);
    expect(onDelete).toHaveBeenCalledWith("doc-uuid-1234");
  });

  it("renders process button for queued document and handles trigger", async () => {
    const onProcess = vi.fn().mockResolvedValue(undefined);
    const queuedDoc: DocumentItem = {
      ...sampleDocument,
      id: "doc-queued-1",
      status: "queued",
    };

    renderWithAuth(
      <DocumentList
        documents={[queuedDoc]}
        isLoading={false}
        error={null}
        onRefresh={vi.fn()}
        onDeleteDocument={vi.fn()}
        onProcessDocument={onProcess}
      />
    );

    const processBtn = screen.getByTestId("process-btn-doc-queued-1");
    expect(processBtn).toBeInTheDocument();
    expect(processBtn).toHaveTextContent("Process");

    await userEvent.click(processBtn);
    expect(onProcess).toHaveBeenCalledWith("doc-queued-1");
  });

  it("renders view pages button and expands extracted pages panel on click", async () => {
    const mockPages = [
      {
        page_id: "page-1",
        document_id: sampleDocument.id,
        page_number: 1,
        text: "Section 1: The Tenant shall pay rent monthly.",
        extraction_method: "native" as const,
        char_count: 45,
        word_count: 8,
        ocr_required: false,
      },
    ];

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "success",
        count: 1,
        pages: mockPages,
      }),
    });
    globalThis.fetch = mockFetch;

    renderWithAuth(
      <DocumentList
        documents={[sampleDocument]}
        isLoading={false}
        error={null}
        onRefresh={vi.fn()}
        onDeleteDocument={vi.fn()}
      />
    );

    const viewPagesBtn = screen.getByTestId("view-pages-btn-doc-uuid-1234");
    expect(viewPagesBtn).toBeInTheDocument();
    expect(viewPagesBtn).toHaveTextContent("View Pages");

    await userEvent.click(viewPagesBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        `/api/documents/${sampleDocument.id}/pages`,
        { headers: { Authorization: "Bearer valid-mock-jwt" } }
      );
    });

    expect(
      await screen.findByTestId("pages-panel-doc-uuid-1234")
    ).toBeInTheDocument();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
    expect(screen.getByTestId("page-method-1")).toHaveTextContent("NATIVE");
    expect(screen.getByText(/Section 1: The Tenant/)).toBeInTheDocument();

    // Clicking again collapses the panel
    await userEvent.click(viewPagesBtn);
    expect(
      screen.queryByTestId("pages-panel-doc-uuid-1234")
    ).not.toBeInTheDocument();
  });
});

describe("DocumentsManager Integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches and displays documents on authenticated load", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "success",
        count: 1,
        documents: [sampleDocument],
      }),
    });
    globalThis.fetch = mockFetch;

    renderWithAuth(<DocumentsManager />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("/api/documents", {
        headers: { Authorization: "Bearer valid-mock-jwt" },
      });
    });

    expect(await screen.findByText("lease_agreement.pdf")).toBeInTheDocument();
  });

  it("triggers process API call when process is invoked", async () => {
    const queuedDoc: DocumentItem = {
      ...sampleDocument,
      id: "doc-queued-2",
      status: "queued",
    };

    const mockFetch = vi
      .fn()
      .mockImplementation((url: string, options?: RequestInit) => {
        if (
          url === "/api/documents" &&
          (!options || !options.method || options.method === "GET")
        ) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "success",
              count: 1,
              documents: [queuedDoc],
            }),
          });
        }
        if (url === "/api/documents/doc-queued-2/process") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "success",
              document_id: "doc-queued-2",
              page_count: 1,
              pages: [],
            }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
    globalThis.fetch = mockFetch;

    renderWithAuth(<DocumentsManager />);

    const processBtn = await screen.findByTestId("process-btn-doc-queued-2");
    await userEvent.click(processBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/documents/doc-queued-2/process",
        expect.objectContaining({
          method: "POST",
          headers: { Authorization: "Bearer valid-mock-jwt" },
        })
      );
    });
  });
});
