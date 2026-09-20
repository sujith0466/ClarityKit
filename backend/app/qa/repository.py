import json
import logging
from abc import ABC, abstractmethod

from psycopg2.extensions import connection

from app.database import get_db_connection
from app.qa.models import (
    QAMessage,
    QASession,
)

logger = logging.getLogger(__name__)


class QARepository(ABC):
    """Abstract repository for Q&A session and message persistence."""

    @abstractmethod
    def create_session(self, session: QASession, user_id: str) -> QASession:
        """Create and store a new Q&A session."""
        pass

    @abstractmethod
    def get_session(self, session_id: str, user_id: str) -> QASession | None:
        """Retrieve a session by ID enforcing document ownership."""
        pass

    @abstractmethod
    def list_sessions_by_document(
        self, document_id: str, user_id: str
    ) -> list[QASession]:
        """List all sessions for an owned document."""
        pass

    @abstractmethod
    def save_message(self, message: QAMessage, user_id: str) -> QAMessage:
        """Persist a Q&A exchange message."""
        pass

    @abstractmethod
    def get_messages_by_session(self, session_id: str, user_id: str) -> list[QAMessage]:
        """Get all messages for an owned session in chronological order."""
        pass

    @abstractmethod
    def get_messages_by_document(
        self, document_id: str, user_id: str
    ) -> list[QAMessage]:
        """Get all messages across sessions for an owned document."""
        pass

    @abstractmethod
    def get_message_by_id(self, message_id: str, user_id: str) -> QAMessage | None:
        """Get a single Q&A message by ID."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session and cascade its messages."""
        pass


class InMemoryQARepository(QARepository):
    """In-memory Q&A repository for isolated unit tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, QASession] = {}
        self._session_owners: dict[str, str] = {}  # session_id -> user_id
        self._messages: dict[str, QAMessage] = {}
        self._message_owners: dict[str, str] = {}  # message_id -> user_id

    def create_session(self, session: QASession, user_id: str) -> QASession:
        self._sessions[session.id] = session
        self._session_owners[session.id] = user_id
        return session

    def get_session(self, session_id: str, user_id: str) -> QASession | None:
        if self._session_owners.get(session_id) != user_id:
            return None
        sess = self._sessions.get(session_id)
        if not sess:
            return None
        # Attach messages
        sess.messages = self.get_messages_by_session(session_id, user_id)
        return sess

    def list_sessions_by_document(
        self, document_id: str, user_id: str
    ) -> list[QASession]:
        results: list[QASession] = []
        for sess in self._sessions.values():
            if (
                sess.document_id == document_id
                and self._session_owners.get(sess.id) == user_id
            ):
                sess_copy = QASession(
                    id=sess.id,
                    document_id=sess.document_id,
                    title=sess.title,
                    created_at=sess.created_at,
                    updated_at=sess.updated_at,
                    messages=self.get_messages_by_session(sess.id, user_id),
                )
                results.append(sess_copy)
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def save_message(self, message: QAMessage, user_id: str) -> QAMessage:
        self._messages[message.id] = message
        self._message_owners[message.id] = user_id
        return message

    def get_messages_by_session(self, session_id: str, user_id: str) -> list[QAMessage]:
        results: list[QAMessage] = []
        for msg in self._messages.values():
            if (
                msg.session_id == session_id
                and self._message_owners.get(msg.id) == user_id
            ):
                results.append(msg)
        return sorted(results, key=lambda m: m.created_at)

    def get_messages_by_document(
        self, document_id: str, user_id: str
    ) -> list[QAMessage]:
        results: list[QAMessage] = []
        for msg in self._messages.values():
            if (
                msg.document_id == document_id
                and self._message_owners.get(msg.id) == user_id
            ):
                results.append(msg)
        return sorted(results, key=lambda m: m.created_at)

    def get_message_by_id(self, message_id: str, user_id: str) -> QAMessage | None:
        if self._message_owners.get(message_id) != user_id:
            return None
        return self._messages.get(message_id)

    def delete_session(self, session_id: str, user_id: str) -> bool:
        if self._session_owners.get(session_id) != user_id:
            return False
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._session_owners[session_id]
            # Delete associated messages
            to_delete = [
                mid for mid, m in self._messages.items() if m.session_id == session_id
            ]
            for mid in to_delete:
                del self._messages[mid]
                if mid in self._message_owners:
                    del self._message_owners[mid]
            return True
        return False

    def clear(self) -> None:
        self._sessions.clear()
        self._session_owners.clear()
        self._messages.clear()
        self._message_owners.clear()


class PostgresQARepository(QARepository):
    """PostgreSQL implementation of QARepository with tenant isolation."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _get_conn(self) -> connection:
        return get_db_connection(self._database_url)

    def create_session(self, session: QASession, user_id: str) -> QASession:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Validate ownership of document first
                cur.execute(
                    "SELECT 1 FROM documents WHERE id = %s AND user_id = %s;",
                    (session.document_id, user_id),
                )
                if not cur.fetchone():
                    raise PermissionError("User does not own document.")

                cur.execute(
                    """
                    INSERT INTO qa_sessions (
                        id, document_id, title, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, document_id, title, created_at, updated_at;
                    """,
                    (
                        session.id,
                        session.document_id,
                        session.title,
                        session.created_at,
                        session.updated_at,
                    ),
                )
                conn.commit()
                row = cur.fetchone()
                return QASession(
                    id=str(row[0]),
                    document_id=str(row[1]),
                    title=row[2],
                    created_at=row[3].isoformat()
                    if hasattr(row[3], "isoformat")
                    else str(row[3]),
                    updated_at=row[4].isoformat()
                    if hasattr(row[4], "isoformat")
                    else str(row[4]),
                )
        finally:
            conn.close()

    def get_session(self, session_id: str, user_id: str) -> QASession | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.document_id, s.title, s.created_at, s.updated_at
                    FROM qa_sessions s
                    JOIN documents d ON d.id = s.document_id
                    WHERE s.id = %s AND d.user_id = %s;
                    """,
                    (session_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                session = QASession(
                    id=str(row[0]),
                    document_id=str(row[1]),
                    title=row[2],
                    created_at=row[3].isoformat()
                    if hasattr(row[3], "isoformat")
                    else str(row[3]),
                    updated_at=row[4].isoformat()
                    if hasattr(row[4], "isoformat")
                    else str(row[4]),
                )
                session.messages = self.get_messages_by_session(session_id, user_id)
                return session
        finally:
            conn.close()

    def list_sessions_by_document(
        self, document_id: str, user_id: str
    ) -> list[QASession]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.document_id, s.title, s.created_at, s.updated_at
                    FROM qa_sessions s
                    JOIN documents d ON d.id = s.document_id
                    WHERE s.document_id = %s AND d.user_id = %s
                    ORDER BY s.created_at DESC;
                    """,
                    (document_id, user_id),
                )
                rows = cur.fetchall()
                sessions: list[QASession] = []
                for row in rows:
                    sess = QASession(
                        id=str(row[0]),
                        document_id=str(row[1]),
                        title=row[2],
                        created_at=row[3].isoformat()
                        if hasattr(row[3], "isoformat")
                        else str(row[3]),
                        updated_at=row[4].isoformat()
                        if hasattr(row[4], "isoformat")
                        else str(row[4]),
                    )
                    sessions.append(sess)
                return sessions
        finally:
            conn.close()

    def save_message(self, message: QAMessage, user_id: str) -> QAMessage:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Check document ownership
                cur.execute(
                    "SELECT 1 FROM documents WHERE id = %s AND user_id = %s;",
                    (message.document_id, user_id),
                )
                if not cur.fetchone():
                    raise PermissionError("User does not own document.")

                claims_json = json.dumps([c.to_dict() for c in message.claims])
                refs_json = json.dumps(message.evidence_references)

                cur.execute(
                    """
                    INSERT INTO qa_messages (
                        id, session_id, document_id, question_text, answer_text,
                        trust_tier, safety_status, evidence_coverage, is_grounded,
                        claims, evidence_references, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, document_id, question_text, answer_text,
                              trust_tier, safety_status, evidence_coverage, is_grounded,
                              claims, evidence_references, created_at;
                    """,
                    (
                        message.id,
                        message.session_id,
                        message.document_id,
                        message.question_text,
                        message.answer_text,
                        message.trust_tier.value,
                        message.safety_status.value,
                        message.evidence_coverage,
                        message.is_grounded,
                        claims_json,
                        refs_json,
                        message.created_at,
                    ),
                )
                # Update session updated_at
                cur.execute(
                    "UPDATE qa_sessions SET updated_at = NOW() WHERE id = %s;",
                    (message.session_id,),
                )
                conn.commit()
                return message
        finally:
            conn.close()

    def get_messages_by_session(self, session_id: str, user_id: str) -> list[QAMessage]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.id, m.session_id, m.document_id, m.question_text,
                           m.answer_text, m.trust_tier, m.safety_status,
                           m.evidence_coverage, m.is_grounded, m.claims,
                           m.evidence_references, m.created_at
                    FROM qa_messages m
                    JOIN documents d ON d.id = m.document_id
                    WHERE m.session_id = %s AND d.user_id = %s
                    ORDER BY m.created_at ASC;
                    """,
                    (session_id, user_id),
                )
                rows = cur.fetchall()
                messages: list[QAMessage] = []
                for row in rows:
                    claims_data = row[9]
                    if isinstance(claims_data, str):
                        claims_data = json.loads(claims_data)
                    refs_data = row[10]
                    if isinstance(refs_data, str):
                        refs_data = json.loads(refs_data)

                    msg = QAMessage.from_dict(
                        {
                            "id": str(row[0]),
                            "session_id": str(row[1]),
                            "document_id": str(row[2]),
                            "question_text": row[3],
                            "answer_text": row[4],
                            "trust_tier": row[5],
                            "safety_status": row[6],
                            "evidence_coverage": float(row[7]),
                            "is_grounded": bool(row[8]),
                            "claims": claims_data,
                            "evidence_references": refs_data,
                            "created_at": row[11].isoformat()
                            if hasattr(row[11], "isoformat")
                            else str(row[11]),
                        }
                    )
                    messages.append(msg)
                return messages
        finally:
            conn.close()

    def get_messages_by_document(
        self, document_id: str, user_id: str
    ) -> list[QAMessage]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.id, m.session_id, m.document_id, m.question_text,
                           m.answer_text, m.trust_tier, m.safety_status,
                           m.evidence_coverage, m.is_grounded, m.claims,
                           m.evidence_references, m.created_at
                    FROM qa_messages m
                    JOIN documents d ON d.id = m.document_id
                    WHERE m.document_id = %s AND d.user_id = %s
                    ORDER BY m.created_at ASC;
                    """,
                    (document_id, user_id),
                )
                rows = cur.fetchall()
                messages: list[QAMessage] = []
                for row in rows:
                    claims_data = row[9]
                    if isinstance(claims_data, str):
                        claims_data = json.loads(claims_data)
                    refs_data = row[10]
                    if isinstance(refs_data, str):
                        refs_data = json.loads(refs_data)

                    msg = QAMessage.from_dict(
                        {
                            "id": str(row[0]),
                            "session_id": str(row[1]),
                            "document_id": str(row[2]),
                            "question_text": row[3],
                            "answer_text": row[4],
                            "trust_tier": row[5],
                            "safety_status": row[6],
                            "evidence_coverage": float(row[7]),
                            "is_grounded": bool(row[8]),
                            "claims": claims_data,
                            "evidence_references": refs_data,
                            "created_at": row[11].isoformat()
                            if hasattr(row[11], "isoformat")
                            else str(row[11]),
                        }
                    )
                    messages.append(msg)
                return messages
        finally:
            conn.close()

    def get_message_by_id(self, message_id: str, user_id: str) -> QAMessage | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.id, m.session_id, m.document_id, m.question_text,
                           m.answer_text, m.trust_tier, m.safety_status,
                           m.evidence_coverage, m.is_grounded, m.claims,
                           m.evidence_references, m.created_at
                    FROM qa_messages m
                    JOIN documents d ON d.id = m.document_id
                    WHERE m.id = %s AND d.user_id = %s;
                    """,
                    (message_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                claims_data = row[9]
                if isinstance(claims_data, str):
                    claims_data = json.loads(claims_data)
                refs_data = row[10]
                if isinstance(refs_data, str):
                    refs_data = json.loads(refs_data)

                return QAMessage.from_dict(
                    {
                        "id": str(row[0]),
                        "session_id": str(row[1]),
                        "document_id": str(row[2]),
                        "question_text": row[3],
                        "answer_text": row[4],
                        "trust_tier": row[5],
                        "safety_status": row[6],
                        "evidence_coverage": float(row[7]),
                        "is_grounded": bool(row[8]),
                        "claims": claims_data,
                        "evidence_references": refs_data,
                        "created_at": row[11].isoformat()
                        if hasattr(row[11], "isoformat")
                        else str(row[11]),
                    }
                )
        finally:
            conn.close()

    def delete_session(self, session_id: str, user_id: str) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM qa_sessions s
                    USING documents d
                    WHERE s.document_id = d.id AND s.id = %s AND d.user_id = %s;
                    """,
                    (session_id, user_id),
                )
                conn.commit()
                return bool(cur.rowcount > 0)
        finally:
            conn.close()


in_memory_qa_repository = InMemoryQARepository()


def get_qa_repository(database_url: str | None = None) -> QARepository:
    """Return configured repository implementation."""
    from app.config import Config

    url = database_url or Config.DATABASE_URL
    if url:
        return PostgresQARepository(database_url=url)
    return in_memory_qa_repository
