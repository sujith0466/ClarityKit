import React, { useState } from "react";
import { RetrievalResult, RetrievalSearchResponse } from "../../types/document";
import { useAuth } from "../../context/useAuth";

export const RetrievalSearch: React.FC = () => {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<readonly RetrievalResult[]>([]);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !token) return;

    setIsLoading(true);
    setError(null);
    setSearched(true);

    try {
      const response = await fetch("/api/retrieval/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: query.trim(),
          top_k: topK,
        }),
      });

      const data = (await response.json()) as RetrievalSearchResponse & {
        message?: string;
      };

      if (!response.ok) {
        setError(data.message || "Failed to execute semantic search.");
        setResults([]);
        return;
      }

      setResults(data.results || []);
    } catch {
      setError("Network error while performing search.");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section
      className="card retrieval-search-card"
      aria-labelledby="retrieval-heading"
      data-testid="retrieval-search-section"
    >
      <div className="retrieval-search-header">
        <h2 id="retrieval-heading">Semantic Vector Retrieval</h2>
        <p>
          Search across your indexed legal document chunks using vector cosine
          similarity.
        </p>
      </div>

      <form
        onSubmit={handleSearch}
        className="search-form"
        data-testid="search-form"
      >
        <div className="form-group">
          <label htmlFor="search-query">Search Query</label>
          <div className="search-input-group">
            <input
              id="search-query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search phrase or clause topic..."
              data-testid="search-input"
              required
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={isLoading || !query.trim()}
              data-testid="search-btn"
            >
              {isLoading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>

        <div className="search-options">
          <label htmlFor="top-k-select">Max Results:</label>
          <select
            id="top-k-select"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            data-testid="top-k-select"
          >
            <option value={3}>3</option>
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
          </select>
        </div>
      </form>

      {error && (
        <div
          className="auth-error-banner"
          role="alert"
          aria-live="assertive"
          data-testid="search-error"
        >
          {error}
        </div>
      )}

      {isLoading && (
        <div className="loading-state" data-testid="search-loading">
          <p>Retrieving matching chunks...</p>
        </div>
      )}

      {!isLoading && searched && results.length === 0 && !error && (
        <div className="empty-state" data-testid="search-empty">
          <p>No matching chunks found.</p>
          <span>
            Ensure your documents have been processed and indexed before
            searching.
          </span>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results-container" data-testid="search-results">
          <div className="search-results-header">
            <h3>Retrieved Chunks ({results.length})</h3>
            <span className="retrieval-disclaimer">
              * Retrieval scores reflect mathematical vector similarity only and
              do not indicate legal accuracy or validity.
            </span>
          </div>

          <div className="results-list">
            {results.map((result) => (
              <div
                key={result.chunk_id}
                className="result-chunk-card"
                data-testid={`search-result-${result.chunk_id}`}
              >
                <div className="result-chunk-header">
                  <span className="chunk-provenance-tag">
                    {result.page_start === result.page_end
                      ? `Page ${result.page_start}`
                      : `Pages ${result.page_start}�${result.page_end}`}{" "}
                    (Chunk #{result.chunk_index})
                  </span>
                  <span
                    className="similarity-badge"
                    data-testid={`similarity-score-${result.chunk_id}`}
                  >
                    Cosine Similarity: {result.similarity.toFixed(4)}
                  </span>
                </div>
                <div className="result-chunk-body">
                  <p>{result.text}</p>
                </div>
                <div className="result-chunk-footer">
                  <span>
                    {result.word_count} words | {result.char_count} chars
                  </span>
                  <span className="doc-id-ref">
                    Doc: <code>{result.document_id}</code>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
