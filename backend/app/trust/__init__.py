"""Trust & Safety layer for ClarityKit.

Provides deterministic claim classification, four-tier trust modeling,
evidence-dependent fact verification, professional review escalation,
and multi-tenant safety management.
"""

from .classifier import TrustClassifier
from .models import (
    AssessedClaim,
    DocumentTrustReport,
    LimitationType,
    SafetyStatus,
    TrustAssessment,
    TrustError,
    TrustTier,
)
from .repository import (
    InMemoryTrustRepository,
    PgTrustRepository,
    TrustRepository,
    get_trust_repository,
)
from .rules import TrustRule, get_default_trust_rules
from .service import TrustService

__all__ = [
    "AssessedClaim",
    "DocumentTrustReport",
    "InMemoryTrustRepository",
    "LimitationType",
    "PgTrustRepository",
    "SafetyStatus",
    "TrustAssessment",
    "TrustClassifier",
    "TrustError",
    "TrustRepository",
    "TrustRule",
    "TrustService",
    "TrustTier",
    "get_default_trust_rules",
    "get_trust_repository",
]
