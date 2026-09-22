"""Deterministic Structured Comparison and Candidate Matching Engine (Phase 13)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from app.comparison.models import (
    ComparisonCategory,
    ComparisonFinding,
    DifferenceClassification,
    DocumentEvidenceRef,
)
from app.evidence.models import EvidenceValidationStatus
from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
)
from app.trust.models import SafetyStatus, TrustTier


def _normalize_str(text: str) -> str:
    """Normalize string for robust token matching."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_number_of_days(text: str) -> int | None:
    """Extract numeric days count from text like '30 days', '60 calendar days'."""
    match = re.search(r"(\d+)\s+(?:business\s+|calendar\s+)?days?", text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


class ComparisonMatcher:
    """Deterministic comparison engine across structured extractions."""

    @classmethod
    def compare_documents(
        cls,
        doc_ids: Sequence[str],
        doc_titles: dict[str, str],
        extractions: dict[str, DocumentUnderstanding],
    ) -> list[ComparisonFinding]:
        """Perform deterministic cross-document comparison across categories."""
        findings: list[ComparisonFinding] = []

        # 1. Compare Parties
        findings.extend(cls._compare_parties(doc_ids, doc_titles, extractions))

        # 2. Compare Dates
        findings.extend(cls._compare_dates(doc_ids, doc_titles, extractions))

        # 3. Compare Obligations & Notice Periods
        findings.extend(cls._compare_obligations(doc_ids, doc_titles, extractions))

        # 4. Compare Clauses
        findings.extend(cls._compare_clauses(doc_ids, doc_titles, extractions))

        return findings

    @classmethod
    def _compare_parties(
        cls,
        doc_ids: Sequence[str],
        doc_titles: dict[str, str],
        extractions: dict[str, DocumentUnderstanding],
    ) -> list[ComparisonFinding]:
        findings: list[ComparisonFinding] = []
        doc_a_id = doc_ids[0]
        doc_b_id = doc_ids[1]

        und_a = extractions.get(doc_a_id)
        parties_a: list[ExtractedParty] = und_a.parties if und_a else []
        und_b = extractions.get(doc_b_id)
        parties_b: list[ExtractedParty] = und_b.parties if und_b else []

        matched_b_indices: set[int] = set()

        for pa in parties_a:
            norm_a_name = _normalize_str(pa.name)
            matched_b_idx: int | None = None

            for idx, pb in enumerate(parties_b):
                if idx in matched_b_indices:
                    continue
                norm_b_name = _normalize_str(pb.name)
                # Match if identical normalized name or substring
                if (
                    norm_a_name == norm_b_name
                    or (len(norm_a_name) > 3 and norm_a_name in norm_b_name)
                    or (len(norm_b_name) > 3 and norm_b_name in norm_a_name)
                ):
                    matched_b_idx = idx
                    break

            if matched_b_idx is not None:
                matched_b_indices.add(matched_b_idx)
                pb = parties_b[matched_b_idx]

                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=pa.page_number,
                        page_end=pa.page_number,
                        source_span=pa.source_span,
                        section="Parties",
                        exact_quote=f"Party: {pa.name} (Role: {pa.role})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=pb.page_number,
                        page_end=pb.page_number,
                        source_span=pb.source_span,
                        section="Parties",
                        exact_quote=f"Party: {pb.name} (Role: {pb.role})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                ]

                # Check if roles match
                if _normalize_str(pa.role) == _normalize_str(pb.role):
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.PARTIES,
                            title=f"Consistent Party Designation: {pa.name}",
                            description=(
                                f"Both {doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} identify "
                                f"'{pa.name}' in the role of '{pa.role}'."
                            ),
                            classification=DifferenceClassification.MATCH,
                            evidence_references=evidence,
                            lawyer_questions=[],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
                else:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.PARTIES,
                            title=f"Differing Party Role: {pa.name}",
                            description=(
                                f"'{pa.name}' is designated as '{pa.role}' in "
                                f"{doc_titles.get(doc_a_id, 'Document A')} but as "
                                f"'{pb.role}' in "
                                f"{doc_titles.get(doc_b_id, 'Document B')}."
                            ),
                            classification=DifferenceClassification.DIFFERENT,
                            evidence_references=evidence,
                            lawyer_questions=[
                                f"Does the difference in designated roles for "
                                f"'{pa.name}' ('{pa.role}' vs '{pb.role}') alter "
                                f"the scope of responsibility or liability between "
                                f"these agreements?"
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
            else:
                # Present in Doc A only
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=pa.page_number,
                        page_end=pa.page_number,
                        source_span=pa.source_span,
                        section="Parties",
                        exact_quote=f"Party: {pa.name} (Role: {pa.role})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.PARTIES,
                        title=(
                            f"Party Identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')}: {pa.name}"
                        ),
                        description=(
                            f"A corresponding party designation for '{pa.name}' "
                            f"({pa.role}) was identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_b_id, 'Document B')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Is '{pa.name}' intended to be a party or beneficiary "
                            f"under {doc_titles.get(doc_b_id, 'Document B')} as well?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Remaining in Doc B only
        for idx, pb in enumerate(parties_b):
            if idx not in matched_b_indices:
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=pb.page_number,
                        page_end=pb.page_number,
                        source_span=pb.source_span,
                        section="Parties",
                        exact_quote=f"Party: {pb.name} (Role: {pb.role})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.PARTIES,
                        title=(
                            f"Party Identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')}: {pb.name}"
                        ),
                        description=(
                            f"A corresponding party designation for '{pb.name}' "
                            f"({pb.role}) was identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_a_id, 'Document A')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Is '{pb.name}' intended to be bound by "
                            f"{doc_titles.get(doc_a_id, 'Document A')}?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _compare_dates(
        cls,
        doc_ids: Sequence[str],
        doc_titles: dict[str, str],
        extractions: dict[str, DocumentUnderstanding],
    ) -> list[ComparisonFinding]:
        findings: list[ComparisonFinding] = []
        doc_a_id = doc_ids[0]
        doc_b_id = doc_ids[1]

        und_a = extractions.get(doc_a_id)
        dates_a: list[ExtractedDate] = und_a.dates if und_a else []
        und_b = extractions.get(doc_b_id)
        dates_b: list[ExtractedDate] = und_b.dates if und_b else []

        matched_b_indices: set[int] = set()

        for da in dates_a:
            norm_a_type = _normalize_str(da.date_type)
            norm_a_desc = _normalize_str(da.description)
            matched_b_idx: int | None = None

            for idx, db in enumerate(dates_b):
                if idx in matched_b_indices:
                    continue
                norm_b_type = _normalize_str(db.date_type)
                norm_b_desc = _normalize_str(db.description)

                # Match by date type or strong description overlap
                if norm_a_type == norm_b_type or norm_a_desc == norm_b_desc:
                    matched_b_idx = idx
                    break

            if matched_b_idx is not None:
                matched_b_indices.add(matched_b_idx)
                db = dates_b[matched_b_idx]

                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=da.page_number,
                        page_end=da.page_number,
                        source_span=da.source_span,
                        section="Dates",
                        exact_quote=f"Date: {da.raw_text} ({da.description})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=db.page_number,
                        page_end=db.page_number,
                        source_span=db.source_span,
                        section="Dates",
                        exact_quote=f"Date: {db.raw_text} ({db.description})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                ]

                # Check if normalized date values match
                iso_a = da.normalized_date or da.raw_text.strip()
                iso_b = db.normalized_date or db.raw_text.strip()

                if iso_a and iso_b and iso_a == iso_b:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.DATES,
                            title=(
                                f"Consistent Date: {da.description or da.date_type}"
                            ),
                            description=(
                                f"Both {doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} state "
                                f"the date '{da.raw_text}' for "
                                f"{da.description or da.date_type}."
                            ),
                            classification=DifferenceClassification.MATCH,
                            evidence_references=evidence,
                            lawyer_questions=[],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
                else:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.DATES,
                            title=(
                                f"Potential Date Inconsistency: "
                                f"{da.description or da.date_type}"
                            ),
                            description=(
                                f"{doc_titles.get(doc_a_id, 'Document A')} states "
                                f"'{da.raw_text}' while "
                                f"{doc_titles.get(doc_b_id, 'Document B')} states "
                                f"'{db.raw_text}' for "
                                f"{da.description or da.date_type}."
                            ),
                            classification=DifferenceClassification.POTENTIAL_INCONSISTENCY,
                            evidence_references=evidence,
                            lawyer_questions=[
                                f"Which date ('{da.raw_text}' or '{db.raw_text}') "
                                f"is intended to govern "
                                f"{da.description or da.date_type}, and did a "
                                f"subsequent document supersede the earlier one?"
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
            else:
                # Date present in Doc A only
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=da.page_number,
                        page_end=da.page_number,
                        source_span=da.source_span,
                        section="Dates",
                        exact_quote=f"Date: {da.raw_text} ({da.description})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.DATES,
                        title=(
                            f"Date Specified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')}: "
                            f"{da.description or da.date_type}"
                        ),
                        description=(
                            f"A corresponding date specification for "
                            f"{da.description or da.date_type} ('{da.raw_text}') "
                            f"was identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_b_id, 'Document B')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Does the date '{da.raw_text}' specified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} apply to "
                            f"the obligations in "
                            f"{doc_titles.get(doc_b_id, 'Document B')}?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Dates in Doc B only
        for idx, db in enumerate(dates_b):
            if idx not in matched_b_indices:
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=db.page_number,
                        page_end=db.page_number,
                        source_span=db.source_span,
                        section="Dates",
                        exact_quote=f"Date: {db.raw_text} ({db.description})",
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.DATES,
                        title=(
                            f"Date Specified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')}: "
                            f"{db.description or db.date_type}"
                        ),
                        description=(
                            f"A corresponding date specification for "
                            f"{db.description or db.date_type} ('{db.raw_text}') "
                            f"was identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_a_id, 'Document A')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Does the date '{db.raw_text}' specified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} apply to "
                            f"the obligations in "
                            f"{doc_titles.get(doc_a_id, 'Document A')}?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _compare_obligations(
        cls,
        doc_ids: Sequence[str],
        doc_titles: dict[str, str],
        extractions: dict[str, DocumentUnderstanding],
    ) -> list[ComparisonFinding]:
        findings: list[ComparisonFinding] = []
        doc_a_id = doc_ids[0]
        doc_b_id = doc_ids[1]

        und_a = extractions.get(doc_a_id)
        obs_a: list[ExtractedObligation] = und_a.obligations if und_a else []
        und_b = extractions.get(doc_b_id)
        obs_b: list[ExtractedObligation] = und_b.obligations if und_b else []

        matched_b_indices: set[int] = set()

        for oa in obs_a:
            norm_a_obligor = _normalize_str(oa.obligor)
            norm_a_duty = _normalize_str(oa.duty)
            days_a = _extract_number_of_days(oa.duty + " " + (oa.deadline or ""))

            matched_b_idx: int | None = None

            for idx, ob in enumerate(obs_b):
                if idx in matched_b_indices:
                    continue
                norm_b_obligor = _normalize_str(ob.obligor)
                norm_b_duty = _normalize_str(ob.duty)
                days_b = _extract_number_of_days(ob.duty + " " + (ob.deadline or ""))

                # Check if notice or termination obligation topic matches
                is_notice_a = "notice" in norm_a_duty or "terminat" in norm_a_duty
                is_notice_b = "notice" in norm_b_duty or "terminat" in norm_b_duty

                if (is_notice_a and is_notice_b) or (
                    norm_a_obligor == norm_b_obligor
                    and (
                        norm_a_duty in norm_b_duty
                        or norm_b_duty in norm_a_duty
                        or (days_a is not None and days_b is not None)
                    )
                ):
                    matched_b_idx = idx
                    break

            if matched_b_idx is not None:
                matched_b_indices.add(matched_b_idx)
                ob = obs_b[matched_b_idx]
                days_b = _extract_number_of_days(ob.duty + " " + (ob.deadline or ""))

                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=oa.page_start,
                        page_end=oa.page_end,
                        source_span=oa.source_span,
                        section="Obligations",
                        exact_quote=(
                            f"Obligor: {oa.obligor} | Duty: {oa.duty}"
                            + (f" | Deadline: {oa.deadline}" if oa.deadline else "")
                        ),
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=ob.page_start,
                        page_end=ob.page_end,
                        source_span=ob.source_span,
                        section="Obligations",
                        exact_quote=(
                            f"Obligor: {ob.obligor} | Duty: {ob.duty}"
                            + (f" | Deadline: {ob.deadline}" if ob.deadline else "")
                        ),
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                ]

                # Check if notice period days differ
                if days_a is not None and days_b is not None and days_a != days_b:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.NOTICE,
                            title=(
                                f"Notice Period Discrepancy: {days_a} vs {days_b} Days"
                            ),
                            description=(
                                f"{doc_titles.get(doc_a_id, 'Document A')} specifies "
                                f"{days_a} days for '{oa.duty}' whereas "
                                f"{doc_titles.get(doc_b_id, 'Document B')} specifies "
                                f"{days_b} days for '{ob.duty}'."
                            ),
                            classification=DifferenceClassification.POTENTIAL_INCONSISTENCY,
                            evidence_references=evidence,
                            lawyer_questions=[
                                f"Which notice period ({days_a} days in "
                                f"{doc_titles.get(doc_a_id, 'Document A')} or "
                                f"{days_b} days in "
                                f"{doc_titles.get(doc_b_id, 'Document B')}) "
                                f"governs, and does one document amend or "
                                f"supersede the other?"
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
                elif norm_a_duty == norm_b_duty:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.OBLIGATIONS,
                            title=f"Consistent Obligation: {oa.obligor}",
                            description=(
                                f"Both {doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} state "
                                f"the same obligation for {oa.obligor}: '{oa.duty}'."
                            ),
                            classification=DifferenceClassification.MATCH,
                            evidence_references=evidence,
                            lawyer_questions=[],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
                else:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=ComparisonCategory.OBLIGATIONS,
                            title=f"Differing Obligation Terms: {oa.obligor}",
                            description=(
                                f"{doc_titles.get(doc_a_id, 'Document A')} requires "
                                f"'{oa.duty}' whereas "
                                f"{doc_titles.get(doc_b_id, 'Document B')} specifies "
                                f"'{ob.duty}'."
                            ),
                            classification=DifferenceClassification.DIFFERENT,
                            evidence_references=evidence,
                            lawyer_questions=[
                                f"How do the differing obligation terms between "
                                f"{doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} interact "
                                f"in practice?"
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
            else:
                # Present in Doc A only
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=oa.page_start,
                        page_end=oa.page_end,
                        source_span=oa.source_span,
                        section="Obligations",
                        exact_quote=(
                            f"Obligor: {oa.obligor} | Duty: {oa.duty}"
                            + (f" | Deadline: {oa.deadline}" if oa.deadline else "")
                        ),
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.OBLIGATIONS,
                        title=(
                            f"Obligation Identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')}: {oa.obligor}"
                        ),
                        description=(
                            f"A corresponding obligation for {oa.obligor} "
                            f"('{oa.duty}') was identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_b_id, 'Document B')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Is the obligation on {oa.obligor} ('{oa.duty}') "
                            f"intended to survive or apply under "
                            f"{doc_titles.get(doc_b_id, 'Document B')}?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Obligations in Doc B only
        for idx, ob in enumerate(obs_b):
            if idx not in matched_b_indices:
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=ob.page_start,
                        page_end=ob.page_end,
                        source_span=ob.source_span,
                        section="Obligations",
                        exact_quote=(
                            f"Obligor: {ob.obligor} | Duty: {ob.duty}"
                            + (f" | Deadline: {ob.deadline}" if ob.deadline else "")
                        ),
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=ComparisonCategory.OBLIGATIONS,
                        title=(
                            f"Obligation Identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')}: {ob.obligor}"
                        ),
                        description=(
                            f"A corresponding obligation for {ob.obligor} "
                            f"('{ob.duty}') was identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_a_id, 'Document A')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Is the obligation on {ob.obligor} ('{ob.duty}') "
                            f"intended to apply to "
                            f"{doc_titles.get(doc_a_id, 'Document A')} as well?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _compare_clauses(
        cls,
        doc_ids: Sequence[str],
        doc_titles: dict[str, str],
        extractions: dict[str, DocumentUnderstanding],
    ) -> list[ComparisonFinding]:
        findings: list[ComparisonFinding] = []
        doc_a_id = doc_ids[0]
        doc_b_id = doc_ids[1]

        und_a = extractions.get(doc_a_id)
        clauses_a: list[ExtractedClause] = und_a.clauses if und_a else []
        und_b = extractions.get(doc_b_id)
        clauses_b: list[ExtractedClause] = und_b.clauses if und_b else []

        matched_b_indices: set[int] = set()

        for ca in clauses_a:
            norm_a_cat = _normalize_str(ca.category)
            norm_a_title = _normalize_str(ca.title)
            matched_b_idx: int | None = None

            for idx, cb in enumerate(clauses_b):
                if idx in matched_b_indices:
                    continue
                norm_b_cat = _normalize_str(cb.category)
                norm_b_title = _normalize_str(cb.title)

                # Match by category or title
                if (
                    norm_a_cat == norm_b_cat and norm_a_cat not in ["other", "general"]
                ) or (
                    norm_a_title
                    and (
                        norm_a_title == norm_b_title
                        or (len(norm_a_title) > 4 and norm_a_title in norm_b_title)
                    )
                ):
                    matched_b_idx = idx
                    break

            category_enum = cls._map_clause_category(ca.category)

            if matched_b_idx is not None:
                matched_b_indices.add(matched_b_idx)
                cb = clauses_b[matched_b_idx]

                quote_a = f"Clause {ca.clause_identifier or ''}: {ca.title}".strip()
                quote_b = f"Clause {cb.clause_identifier or ''}: {cb.title}".strip()

                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=ca.page_start,
                        page_end=ca.page_end,
                        source_span=ca.source_span,
                        section=ca.clause_identifier or ca.title,
                        exact_quote=quote_a,
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=cb.page_start,
                        page_end=cb.page_end,
                        source_span=cb.source_span,
                        section=cb.clause_identifier or cb.title,
                        exact_quote=quote_b,
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    ),
                ]

                # Compare clause text
                norm_a_text = _normalize_str(ca.text or ca.source_span)
                norm_b_text = _normalize_str(cb.text or cb.source_span)

                if norm_a_text == norm_b_text:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=category_enum,
                            title=(
                                f"Matching Clause Provision: {ca.title or ca.category}"
                            ),
                            description=(
                                f"Both {doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} contain "
                                f"matching provisions regarding "
                                f"'{ca.title or ca.category}'."
                            ),
                            classification=DifferenceClassification.MATCH,
                            evidence_references=evidence,
                            lawyer_questions=[],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
                else:
                    findings.append(
                        ComparisonFinding(
                            id=str(uuid.uuid4()),
                            category=category_enum,
                            title=(
                                f"Differing Clause Language: {ca.title or ca.category}"
                            ),
                            description=(
                                f"{doc_titles.get(doc_a_id, 'Document A')} and "
                                f"{doc_titles.get(doc_b_id, 'Document B')} state "
                                f"differing language regarding "
                                f"'{ca.title or ca.category}'."
                            ),
                            classification=DifferenceClassification.DIFFERENT,
                            evidence_references=evidence,
                            lawyer_questions=[
                                f"What is the legal significance of the language "
                                f"differences in the {ca.title or ca.category} "
                                f"provisions between these documents?"
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                        )
                    )
            else:
                # Present in Doc A only
                quote_a = f"Clause {ca.clause_identifier or ''}: {ca.title}".strip()
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_a_id,
                        document_title=doc_titles.get(doc_a_id, "Document A"),
                        page_start=ca.page_start,
                        page_end=ca.page_end,
                        source_span=ca.source_span,
                        section=ca.clause_identifier or ca.title,
                        exact_quote=quote_a,
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=category_enum,
                        title=(
                            f"Clause Identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')}: "
                            f"{ca.title or ca.category}"
                        ),
                        description=(
                            f"A corresponding provision for "
                            f"'{ca.title or ca.category}' was identified in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_b_id, 'Document B')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Does the absence of a corresponding "
                            f"'{ca.title or ca.category}' provision in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} create any "
                            f"gaps in protection or rights?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Clauses in Doc B only
        for idx, cb in enumerate(clauses_b):
            if idx not in matched_b_indices:
                category_enum = cls._map_clause_category(cb.category)
                quote_b = f"Clause {cb.clause_identifier or ''}: {cb.title}".strip()
                evidence = [
                    DocumentEvidenceRef(
                        document_id=doc_b_id,
                        document_title=doc_titles.get(doc_b_id, "Document B"),
                        page_start=cb.page_start,
                        page_end=cb.page_end,
                        source_span=cb.source_span,
                        section=cb.clause_identifier or cb.title,
                        exact_quote=quote_b,
                        validation_status=EvidenceValidationStatus.UNVERIFIED,
                        trust_tier=TrustTier.DOCUMENT_FACT,
                    )
                ]
                findings.append(
                    ComparisonFinding(
                        id=str(uuid.uuid4()),
                        category=category_enum,
                        title=(
                            f"Clause Identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')}: "
                            f"{cb.title or cb.category}"
                        ),
                        description=(
                            f"A corresponding provision for "
                            f"'{cb.title or cb.category}' was identified in "
                            f"{doc_titles.get(doc_b_id, 'Document B')} but was "
                            f"not identified in the extracted content of "
                            f"{doc_titles.get(doc_a_id, 'Document A')}."
                        ),
                        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
                        evidence_references=evidence,
                        lawyer_questions=[
                            f"Does the absence of a corresponding "
                            f"'{cb.title or cb.category}' provision in "
                            f"{doc_titles.get(doc_a_id, 'Document A')} create any "
                            f"gaps in protection or rights?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @staticmethod
    def _map_clause_category(cat_str: str) -> ComparisonCategory:
        norm = _normalize_str(cat_str)
        if "terminat" in norm:
            return ComparisonCategory.TERMINATION
        if "pay" in norm or "fee" in norm or "price" in norm or "rent" in norm:
            return ComparisonCategory.PAYMENT
        if "durat" in norm or "term" in norm or "renew" in norm:
            return ComparisonCategory.DURATION
        if "notice" in norm:
            return ComparisonCategory.NOTICE
        if "definit" in norm:
            return ComparisonCategory.DEFINITIONS
        if "obligat" in norm or "duty" in norm or "covenant" in norm:
            return ComparisonCategory.OBLIGATIONS
        return ComparisonCategory.CLAUSE
