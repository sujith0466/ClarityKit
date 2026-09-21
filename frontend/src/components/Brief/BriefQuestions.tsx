import React from "react";
import { BriefQuestion } from "../../types/brief";
import { InspectionTarget } from "../../types/workspace";

interface BriefQuestionsProps {
  readonly questions: readonly BriefQuestion[];
  readonly onInspect?: (target: InspectionTarget) => void;
}

export const BriefQuestions: React.FC<BriefQuestionsProps> = ({
  questions,
  onInspect,
}) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="brief-section-card">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">
          Questions for Your Legal Professional
        </h3>
        <span className="brief-section-count">{questions.length} items</span>
      </div>
      <p className="brief-section-subtext">
        Objective questions grounded in the extracted terms to discuss during
        your attorney consultation:
      </p>

      <ul className="brief-questions-list">
        {questions.map((q, idx) => (
          <li key={`q-${idx}`} className="brief-question-item">
            <div className="brief-question-content">
              <span className="brief-category-badge">
                {q.category.replace(/_/g, " ").toUpperCase()}
              </span>
              <p className="brief-question-text">{q.question}</p>
              {q.rationale && (
                <p className="brief-question-rationale">
                  <em>Rationale:</em> {q.rationale}
                </p>
              )}
            </div>

            {q.related_clause_id && onInspect && (
              <button
                type="button"
                className="btn btn-inspect-link"
                onClick={() =>
                  onInspect({
                    title: `Related Clause: ${q.related_clause_id}`,
                    claimText: q.question,
                    claimType: "brief_question",
                    sourceSpan: q.rationale || q.question,
                  })
                }
                aria-label={`Inspect source for clause ${q.related_clause_id}`}
              >
                Inspect Source ({q.related_clause_id})
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
