import json
from abc import ABC, abstractmethod
from typing import Any

from app.config import Config
from app.database import get_db_connection
from app.trust.models import (
    AssessedClaim,
    LimitationType,
    SafetyStatus,
    TrustAssessment,
    TrustTier,
)


class TrustRepository(ABC):
    """Repository interface for persisting derived trust assessments."""

    @abstractmethod
    def save_assessments(
        self, document_id: str, assessments: list[AssessedClaim]
    ) -> None:
        """Persist or update assessed claims for a document."""
        pass

    @abstractmethod
    def get_by_document(self, document_id: str, user_id: str) -> list[AssessedClaim]:
        """Retrieve assessed claims enforcing user ownership."""
        pass

    @abstractmethod
    def delete_by_document(self, document_id: str, user_id: str) -> int:
        """Delete assessed claims for a document enforcing user ownership."""
        pass


class InMemoryTrustRepository(TrustRepository):
    """In-memory implementation for testing and isolated runs."""

    def __init__(self) -> None:
        self._store: dict[str, list[AssessedClaim]] = {}

    def save_assessments(
        self, document_id: str, assessments: list[AssessedClaim]
    ) -> None:
        self._store[document_id] = list(assessments)

    def get_by_document(self, document_id: str, user_id: str) -> list[AssessedClaim]:
        return list(self._store.get(document_id, []))

    def delete_by_document(self, document_id: str, user_id: str) -> int:
        if document_id in self._store:
            count = len(self._store[document_id])
            del self._store[document_id]
            return count
        return 0


class PgTrustRepository(TrustRepository):
    """PostgreSQL implementation with SQL-level multi-tenant isolation."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _get_connection(self) -> Any:
        return get_db_connection(self._database_url)

    def save_assessments(
        self, document_id: str, assessments: list[AssessedClaim]
    ) -> None:
        if not assessments:
            return

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Delete existing assessments for clean rebuildable persistence
                cur.execute(
                    "DELETE FROM document_trust_assessments WHERE document_id = %s",
                    (document_id,),
                )
                for item in assessments:
                    assessment = item.trust_assessment
                    cur.execute(
                        """
                        INSERT INTO document_trust_assessments (
                            id, document_id, claim_id, claim_text, claim_type,
                            trust_tier, safety_status, evidence_required,
                            evidence_valid, professional_review_required,
                            limitations, reasoning_summary, evidence_data,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s
                        )
                        """,
                        (
                            item.id,
                            document_id,
                            assessment.claim_id,
                            item.claim_text,
                            item.claim_type.value,
                            assessment.trust_tier.value,
                            assessment.safety_status.value,
                            assessment.evidence_required,
                            assessment.evidence_valid,
                            assessment.professional_review_required,
                            json.dumps([lim.value for lim in assessment.limitations]),
                            assessment.reasoning_summary,
                            json.dumps(
                                [item.evidence.to_dict()] if item.evidence else []
                            ),
                            item.created_at,
                        ),
                    )
            conn.commit()

    def get_by_document(self, document_id: str, user_id: str) -> list[AssessedClaim]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT t.id, t.document_id, t.claim_id, t.claim_text,
                           t.claim_type, t.trust_tier, t.safety_status,
                           t.evidence_required, t.evidence_valid,
                           t.professional_review_required, t.limitations,
                           t.reasoning_summary, t.evidence_data, t.created_at
                    FROM document_trust_assessments t
                    JOIN documents d ON d.id = t.document_id
                    WHERE t.document_id = %s AND d.user_id = %s
                    ORDER BY t.created_at ASC
                    """,
                    (document_id, user_id),
                )
                rows = cur.fetchall()

        results: list[AssessedClaim] = []
        for row in rows:
            lim_raw = row[10]
            if isinstance(lim_raw, str):
                lim_list = json.loads(lim_raw)
            else:
                lim_list = lim_raw or []

            ev_raw = row[12]
            if isinstance(ev_raw, str):
                ev_list = json.loads(ev_raw)
            else:
                ev_list = ev_raw or []

            assessment = TrustAssessment(
                claim_id=row[2],
                trust_tier=TrustTier(row[5]),
                safety_status=SafetyStatus(row[6]),
                evidence_required=bool(row[7]),
                evidence_valid=bool(row[8]),
                professional_review_required=bool(row[9]),
                limitations=[LimitationType(lim) for lim in lim_list],
                reasoning_summary=row[11] or "",
            )

            results.append(
                AssessedClaim.from_dict(
                    {
                        "id": row[0],
                        "document_id": row[1],
                        "claim_text": row[3],
                        "claim_type": row[4],
                        "trust_assessment": assessment.to_dict(),
                        "evidence": ev_list,
                        "created_at": row[13].isoformat()
                        if hasattr(row[13], "isoformat")
                        else str(row[13]),
                    }
                )
            )
        return results

    def delete_by_document(self, document_id: str, user_id: str) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_trust_assessments t
                    USING documents d
                    WHERE t.document_id = d.id
                      AND t.document_id = %s
                      AND d.user_id = %s
                    """,
                    (document_id, user_id),
                )
                deleted = cur.rowcount
            conn.commit()
        return int(deleted or 0)


def get_trust_repository() -> TrustRepository:
    """Factory helper to obtain the configured Trust repository."""
    if Config.DATABASE_URL:
        return PgTrustRepository(Config.DATABASE_URL)
    return InMemoryTrustRepository()
