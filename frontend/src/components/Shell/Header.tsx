import React from "react";

export const Header: React.FC = () => {
  return (
    <header className="header" role="banner">
      <h1 className="title">ClarityKit</h1>
      <p className="subtitle">
        Evidence-grounded legal document understanding and preparation platform.
      </p>
      <div
        className="philosophy-badge"
        aria-label="Product Philosophy"
        role="note"
      >
        UNDERSTAND → EXTRACT → EVIDENCE → ASSIST → PREPARE
      </div>
    </header>
  );
};
