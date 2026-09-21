import React from "react";

interface BriefOpenQuestionsProps {
  readonly questions: readonly string[];
}

export const BriefOpenQuestions: React.FC<BriefOpenQuestionsProps> = ({
  questions,
}) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="brief-section-card">
      <div className="brief-section-header">
        <h3 className="brief-section-heading">
          Open Ambiguities &amp; Inconsistencies
        </h3>
        <span className="brief-section-count">{questions.length} items</span>
      </div>
      <p className="brief-section-subtext">
        These points may represent drafting ambiguities, conflicting terms, or
        silences to review with counsel:
      </p>

      <ul className="brief-questions-list">
        {questions.map((q, idx) => (
          <li key={`oq-${idx}`} className="brief-question-item">
            <div className="brief-question-content">
              <span className="brief-category-badge">AMBIGUITY</span>
              <p className="brief-question-text">{q}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
