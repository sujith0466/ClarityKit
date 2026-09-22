"""Deterministic Version Diff Engine (Phase 14).

Performs structured alignment and change classification between Version 1 (Base)
and Version 2 (Revised) extraction structures using neutral, non-judgmental language.
"""

import re
import uuid

from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
)
from app.trust.models import SafetyStatus, TrustTier
from app.version_diff.models import (
    VersionDiffCategory,
    VersionDiffClassification,
    VersionDiffFinding,
    VersionEvidenceRef,
)


class VersionDiffEngine:
    """Computes deterministic version diff findings between Version 1 and Version 2."""

    @classmethod
    def compute_diff(
        cls,
        v1_doc_id: str,
        v1_doc_title: str,
        v1_understanding: DocumentUnderstanding,
        v2_doc_id: str,
        v2_doc_title: str,
        v2_understanding: DocumentUnderstanding,
    ) -> list[VersionDiffFinding]:
        """Generate structured diff findings across parties, dates, obligations, and
        clauses.
        """
        findings: list[VersionDiffFinding] = []

        findings.extend(
            cls._diff_parties(
                v1_doc_id,
                v1_doc_title,
                v1_understanding.parties,
                v2_doc_id,
                v2_doc_title,
                v2_understanding.parties,
            )
        )

        findings.extend(
            cls._diff_dates(
                v1_doc_id,
                v1_doc_title,
                v1_understanding.dates,
                v2_doc_id,
                v2_doc_title,
                v2_understanding.dates,
            )
        )

        findings.extend(
            cls._diff_obligations(
                v1_doc_id,
                v1_doc_title,
                v1_understanding.obligations,
                v2_doc_id,
                v2_doc_title,
                v2_understanding.obligations,
            )
        )

        findings.extend(
            cls._diff_clauses(
                v1_doc_id,
                v1_doc_title,
                v1_understanding.clauses,
                v2_doc_id,
                v2_doc_title,
                v2_understanding.clauses,
            )
        )

        return findings

    @classmethod
    def _diff_parties(
        cls,
        v1_doc_id: str,
        v1_doc_title: str,
        parties_v1: list[ExtractedParty],
        v2_doc_id: str,
        v2_doc_title: str,
        parties_v2: list[ExtractedParty],
    ) -> list[VersionDiffFinding]:
        findings: list[VersionDiffFinding] = []
        matched_v2_indices: set[int] = set()

        for pa in parties_v1:
            name_a = (pa.name or "").strip()
            norm_a = re.sub(r"[^\w\s]", "", name_a.lower())

            matched = False
            for idx, pb in enumerate(parties_v2):
                if idx in matched_v2_indices:
                    continue
                name_b = (pb.name or "").strip()
                norm_b = re.sub(r"[^\w\s]", "", name_b.lower())

                if norm_a == norm_b or (
                    norm_a and norm_b and (norm_a in norm_b or norm_b in norm_a)
                ):
                    matched = True
                    matched_v2_indices.add(idx)

                    ev_v1 = [
                        VersionEvidenceRef(
                            document_id=v1_doc_id,
                            version_label="v1",
                            document_title=v1_doc_title,
                            page_start=pa.page_number,
                            page_end=pa.page_number,
                            source_span=pa.source_span,
                            exact_quote=f"Party: {pa.name} (Role: {pa.role})",
                            section="Parties",
                        )
                    ]
                    ev_v2 = [
                        VersionEvidenceRef(
                            document_id=v2_doc_id,
                            version_label="v2",
                            document_title=v2_doc_title,
                            page_start=pb.page_number,
                            page_end=pb.page_number,
                            source_span=pb.source_span,
                            exact_quote=f"Party: {pb.name} (Role: {pb.role})",
                            section="Parties",
                        )
                    ]

                    if (pa.role or "").strip().lower() == (
                        pb.role or ""
                    ).strip().lower():
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.PARTIES,
                                title=f"Party Unchanged: {pa.name}",
                                description=(
                                    f"Party designation '{pa.name}' ({pa.role}) is "
                                    f"present in both Version 1 and Version 2."
                                ),
                                classification=VersionDiffClassification.UNCHANGED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    else:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.PARTIES,
                                title=f"Party Role Modified: {pa.name}",
                                description=(
                                    f"Party '{pa.name}' role changed from '{pa.role}' "
                                    f"in Version 1 to '{pb.role}' in Version 2."
                                ),
                                classification=VersionDiffClassification.MODIFIED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                lawyer_questions=[
                                    f"Does the change in role for '{pa.name}' "
                                    f"impact party rights?"
                                ],
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    break

            if not matched:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.PARTIES,
                        title=f"Party Removed in Version 2: {pa.name}",
                        description=(
                            f"Party designation '{pa.name}' ({pa.role}) was "
                            f"identified in Version 1 ({v1_doc_title}) but was "
                            f"not identified in Version 2 ({v2_doc_title})."
                        ),
                        classification=VersionDiffClassification.REMOVED,
                        v1_evidence=[
                            VersionEvidenceRef(
                                document_id=v1_doc_id,
                                version_label="v1",
                                document_title=v1_doc_title,
                                page_start=pa.page_number,
                                page_end=pa.page_number,
                                source_span=pa.source_span,
                                exact_quote=f"Party: {pa.name} (Role: {pa.role})",
                                section="Parties",
                            )
                        ],
                        lawyer_questions=[
                            f"Is '{pa.name}' intentionally omitted from Version 2?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Added parties in Version 2 only
        for idx, pb in enumerate(parties_v2):
            if idx not in matched_v2_indices:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.PARTIES,
                        title=f"Party Added in Version 2: {pb.name}",
                        description=(
                            f"Party designation '{pb.name}' ({pb.role}) was "
                            f"identified in Version 2 ({v2_doc_title}) but was "
                            f"not identified in Version 1 ({v1_doc_title})."
                        ),
                        classification=VersionDiffClassification.ADDED,
                        v2_evidence=[
                            VersionEvidenceRef(
                                document_id=v2_doc_id,
                                version_label="v2",
                                document_title=v2_doc_title,
                                page_start=pb.page_number,
                                page_end=pb.page_number,
                                source_span=pb.source_span,
                                exact_quote=f"Party: {pb.name} (Role: {pb.role})",
                                section="Parties",
                            )
                        ],
                        lawyer_questions=[
                            f"What obligations or rights are assigned to new party "
                            f"'{pb.name}' in Version 2?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _diff_dates(
        cls,
        v1_doc_id: str,
        v1_doc_title: str,
        dates_v1: list[ExtractedDate],
        v2_doc_id: str,
        v2_doc_title: str,
        dates_v2: list[ExtractedDate],
    ) -> list[VersionDiffFinding]:
        findings: list[VersionDiffFinding] = []
        matched_v2_indices: set[int] = set()

        for da in dates_v1:
            key_a = (da.description or da.date_type or "").strip().lower()
            matched = False

            for idx, db in enumerate(dates_v2):
                if idx in matched_v2_indices:
                    continue
                key_b = (db.description or db.date_type or "").strip().lower()

                if (
                    key_a
                    and key_b
                    and (key_a == key_b or key_a in key_b or key_b in key_a)
                ):
                    matched = True
                    matched_v2_indices.add(idx)

                    ev_v1 = [
                        VersionEvidenceRef(
                            document_id=v1_doc_id,
                            version_label="v1",
                            document_title=v1_doc_title,
                            page_start=da.page_number,
                            page_end=da.page_number,
                            source_span=da.source_span,
                            exact_quote=(
                                f"Date: {da.raw_text} "
                                f"({da.description or da.date_type})"
                            ).strip(),
                            section="Dates",
                        )
                    ]
                    ev_v2 = [
                        VersionEvidenceRef(
                            document_id=v2_doc_id,
                            version_label="v2",
                            document_title=v2_doc_title,
                            page_start=db.page_number,
                            page_end=db.page_number,
                            source_span=db.source_span,
                            exact_quote=(
                                f"Date: {db.raw_text} "
                                f"({db.description or db.date_type})"
                            ).strip(),
                            section="Dates",
                        )
                    ]

                    # Check if date value changed
                    norm_a = da.normalized_date or da.raw_text
                    norm_b = db.normalized_date or db.raw_text

                    if norm_a == norm_b:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.DATES,
                                title=(
                                    f"Date Unchanged: {da.description or da.date_type}"
                                ),
                                description=(
                                    f"Date specification for "
                                    f"{da.description or da.date_type} "
                                    f"('{da.raw_text}') "
                                    f"is identical in both Version 1 and Version 2."
                                ),
                                classification=VersionDiffClassification.UNCHANGED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    else:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.DATES,
                                title=(
                                    f"Date Modified: {da.description or da.date_type}"
                                ),
                                description=(
                                    f"Date for {da.description or da.date_type} "
                                    f"modified from '{da.raw_text}' in Version 1 "
                                    f"to '{db.raw_text}' in Version 2."
                                ),
                                classification=VersionDiffClassification.MODIFIED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                lawyer_questions=[
                                    f"Does the change in date to '{db.raw_text}' "
                                    f"affect execution or compliance timelines?"
                                ],
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    break

            if not matched:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.DATES,
                        title=(
                            f"Date Removed in Version 2: "
                            f"{da.description or da.date_type}"
                        ),
                        description=(
                            f"Date specification for "
                            f"{da.description or da.date_type} ('{da.raw_text}') "
                            f"was identified in Version 1 but was not in Version 2."
                        ),
                        classification=VersionDiffClassification.REMOVED,
                        v1_evidence=[
                            VersionEvidenceRef(
                                document_id=v1_doc_id,
                                version_label="v1",
                                document_title=v1_doc_title,
                                page_start=da.page_number,
                                page_end=da.page_number,
                                source_span=da.source_span,
                                exact_quote=(
                                    f"Date: {da.raw_text} "
                                    f"({da.description or da.date_type})"
                                ).strip(),
                                section="Dates",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Added dates in Version 2 only
        for idx, db in enumerate(dates_v2):
            if idx not in matched_v2_indices:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.DATES,
                        title=(
                            f"Date Added in Version 2: {db.description or db.date_type}"
                        ),
                        description=(
                            f"Date specification for "
                            f"{db.description or db.date_type} ('{db.raw_text}') "
                            f"was identified in Version 2 but was not in Version 1."
                        ),
                        classification=VersionDiffClassification.ADDED,
                        v2_evidence=[
                            VersionEvidenceRef(
                                document_id=v2_doc_id,
                                version_label="v2",
                                document_title=v2_doc_title,
                                page_start=db.page_number,
                                page_end=db.page_number,
                                source_span=db.source_span,
                                exact_quote=(
                                    f"Date: {db.raw_text} "
                                    f"({db.description or db.date_type})"
                                ).strip(),
                                section="Dates",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _diff_obligations(
        cls,
        v1_doc_id: str,
        v1_doc_title: str,
        obs_v1: list[ExtractedObligation],
        v2_doc_id: str,
        v2_doc_title: str,
        obs_v2: list[ExtractedObligation],
    ) -> list[VersionDiffFinding]:
        findings: list[VersionDiffFinding] = []
        matched_v2_indices: set[int] = set()

        for oa in obs_v1:
            matched = False
            for idx, ob in enumerate(obs_v2):
                if idx in matched_v2_indices:
                    continue

                # Match by obligor and trigger / duty overlap
                same_obligor = (oa.obligor or "").strip().lower() == (
                    ob.obligor or ""
                ).strip().lower()
                same_trigger = bool(
                    oa.trigger
                    and ob.trigger
                    and oa.trigger.strip().lower() == ob.trigger.strip().lower()
                )

                if same_obligor and (
                    same_trigger or oa.duty in ob.duty or ob.duty in oa.duty
                ):
                    matched = True
                    matched_v2_indices.add(idx)

                    ev_v1 = [
                        VersionEvidenceRef(
                            document_id=v1_doc_id,
                            version_label="v1",
                            document_title=v1_doc_title,
                            page_start=oa.page_start,
                            page_end=oa.page_end,
                            source_span=oa.source_span,
                            exact_quote=f"Obligor: {oa.obligor} | Duty: {oa.duty}"
                            + (f" | Deadline: {oa.deadline}" if oa.deadline else ""),
                            section="Obligations",
                        )
                    ]
                    ev_v2 = [
                        VersionEvidenceRef(
                            document_id=v2_doc_id,
                            version_label="v2",
                            document_title=v2_doc_title,
                            page_start=ob.page_start,
                            page_end=ob.page_end,
                            source_span=ob.source_span,
                            exact_quote=f"Obligor: {ob.obligor} | Duty: {ob.duty}"
                            + (f" | Deadline: {ob.deadline}" if ob.deadline else ""),
                            section="Obligations",
                        )
                    ]

                    if (
                        oa.duty.strip().lower() == ob.duty.strip().lower()
                        and (oa.deadline or "").strip().lower()
                        == (ob.deadline or "").strip().lower()
                    ):
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.OBLIGATIONS,
                                title=f"Obligation Unchanged: {oa.obligor}",
                                description=(
                                    f"Obligation for {oa.obligor} ('{oa.duty}') is "
                                    f"identical in both Version 1 and Version 2."
                                ),
                                classification=VersionDiffClassification.UNCHANGED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    else:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=VersionDiffCategory.OBLIGATIONS,
                                title=f"Obligation Modified: {oa.obligor}",
                                description=(
                                    f"Obligation for {oa.obligor} modified from "
                                    f"'{oa.duty}' (Deadline: {oa.deadline or 'None'}) "
                                    f"in Version 1 to '{ob.duty}' "
                                    f"(Deadline: {ob.deadline or 'None'}) in Version 2."
                                ),
                                classification=VersionDiffClassification.MODIFIED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                lawyer_questions=[
                                    f"Does the modified obligation on {oa.obligor} "
                                    f"alter responsibilities or deadlines?"
                                ],
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    break

            if not matched:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.OBLIGATIONS,
                        title=f"Obligation Removed in Version 2: {oa.obligor}",
                        description=(
                            f"Obligation on {oa.obligor} ('{oa.duty}') was "
                            f"identified in Version 1 but was not in Version 2."
                        ),
                        classification=VersionDiffClassification.REMOVED,
                        v1_evidence=[
                            VersionEvidenceRef(
                                document_id=v1_doc_id,
                                version_label="v1",
                                document_title=v1_doc_title,
                                page_start=oa.page_start,
                                page_end=oa.page_end,
                                source_span=oa.source_span,
                                exact_quote=f"Obligor: {oa.obligor} | Duty: {oa.duty}",
                                section="Obligations",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Added obligations in Version 2 only
        for idx, ob in enumerate(obs_v2):
            if idx not in matched_v2_indices:
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=VersionDiffCategory.OBLIGATIONS,
                        title=f"Obligation Added in Version 2: {ob.obligor}",
                        description=(
                            f"Obligation on {ob.obligor} ('{ob.duty}') was "
                            f"identified in Version 2 but was not in Version 1."
                        ),
                        classification=VersionDiffClassification.ADDED,
                        v2_evidence=[
                            VersionEvidenceRef(
                                document_id=v2_doc_id,
                                version_label="v2",
                                document_title=v2_doc_title,
                                page_start=ob.page_start,
                                page_end=ob.page_end,
                                source_span=ob.source_span,
                                exact_quote=f"Obligor: {ob.obligor} | Duty: {ob.duty}",
                                section="Obligations",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @classmethod
    def _diff_clauses(
        cls,
        v1_doc_id: str,
        v1_doc_title: str,
        clauses_v1: list[ExtractedClause],
        v2_doc_id: str,
        v2_doc_title: str,
        clauses_v2: list[ExtractedClause],
    ) -> list[VersionDiffFinding]:
        findings: list[VersionDiffFinding] = []
        matched_v2_indices: set[int] = set()

        for ca in clauses_v1:
            matched = False
            title_a = (ca.title or ca.category or "").strip().lower()
            cat_a = (ca.category or "").strip().lower()

            for idx, cb in enumerate(clauses_v2):
                if idx in matched_v2_indices:
                    continue
                title_b = (cb.title or cb.category or "").strip().lower()
                cat_b = (cb.category or "").strip().lower()

                same_category = (
                    cat_a and cat_b and cat_a != "general" and cat_a == cat_b
                )
                same_title = bool(
                    title_a and title_b and (title_a in title_b or title_b in title_a)
                )

                if same_category or same_title:
                    matched = True
                    matched_v2_indices.add(idx)

                    ev_v1 = [
                        VersionEvidenceRef(
                            document_id=v1_doc_id,
                            version_label="v1",
                            document_title=v1_doc_title,
                            page_start=ca.page_start,
                            page_end=ca.page_end,
                            source_span=ca.source_span,
                            exact_quote=(
                                f"Clause {ca.clause_identifier or ''}: "
                                f"{ca.title}".strip()
                            ),
                            section=ca.clause_identifier or ca.title,
                        )
                    ]
                    ev_v2 = [
                        VersionEvidenceRef(
                            document_id=v2_doc_id,
                            version_label="v2",
                            document_title=v2_doc_title,
                            page_start=cb.page_start,
                            page_end=cb.page_end,
                            source_span=cb.source_span,
                            exact_quote=(
                                f"Clause {cb.clause_identifier or ''}: "
                                f"{cb.title}".strip()
                            ),
                            section=cb.clause_identifier or cb.title,
                        )
                    ]

                    # Compare text
                    text_a = (ca.text or "").strip()
                    text_b = (cb.text or "").strip()

                    cat_enum = cls._map_category(ca.category)

                    if text_a == text_b:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=cat_enum,
                                title=f"Clause Unchanged: {ca.title or ca.category}",
                                description=(
                                    f"Provision for '{ca.title or ca.category}' "
                                    f"contains identical wording across versions."
                                ),
                                classification=VersionDiffClassification.UNCHANGED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    else:
                        findings.append(
                            VersionDiffFinding(
                                id=str(uuid.uuid4()),
                                category=cat_enum,
                                title=f"Clause Modified: {ca.title or ca.category}",
                                description=(
                                    f"Provision for '{ca.title or ca.category}' "
                                    f"contains modified wording between versions."
                                ),
                                classification=VersionDiffClassification.MODIFIED,
                                v1_evidence=ev_v1,
                                v2_evidence=ev_v2,
                                lawyer_questions=[
                                    f"What is the operational effect of the wording "
                                    f"changes in '{ca.title or ca.category}'?"
                                ],
                                trust_tier=TrustTier.DOCUMENT_FACT,
                                safety_status=SafetyStatus.SAFE,
                            )
                        )
                    break

            if not matched:
                cat_enum = cls._map_category(ca.category)
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=cat_enum,
                        title=f"Clause Removed in Version 2: {ca.title or ca.category}",
                        description=(
                            f"Provision for '{ca.title or ca.category}' was "
                            f"identified in Version 1 ({v1_doc_title}) but "
                            f"was not identified in Version 2 ({v2_doc_title})."
                        ),
                        classification=VersionDiffClassification.REMOVED,
                        v1_evidence=[
                            VersionEvidenceRef(
                                document_id=v1_doc_id,
                                version_label="v1",
                                document_title=v1_doc_title,
                                page_start=ca.page_start,
                                page_end=ca.page_end,
                                source_span=ca.source_span,
                                exact_quote=(
                                    f"Clause {ca.clause_identifier or ''}: "
                                    f"{ca.title}".strip()
                                ),
                                section=ca.clause_identifier or ca.title,
                            )
                        ],
                        lawyer_questions=[
                            f"Does the omission of '{ca.title or ca.category}' "
                            f"in Version 2 remove key protections?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        # Added clauses in Version 2 only
        for idx, cb in enumerate(clauses_v2):
            if idx not in matched_v2_indices:
                cat_enum = cls._map_category(cb.category)
                findings.append(
                    VersionDiffFinding(
                        id=str(uuid.uuid4()),
                        category=cat_enum,
                        title=f"Clause Added in Version 2: {cb.title or cb.category}",
                        description=(
                            f"Provision for '{cb.title or cb.category}' was "
                            f"identified in Version 2 ({v2_doc_title}) but "
                            f"was not identified in Version 1 ({v1_doc_title})."
                        ),
                        classification=VersionDiffClassification.ADDED,
                        v2_evidence=[
                            VersionEvidenceRef(
                                document_id=v2_doc_id,
                                version_label="v2",
                                document_title=v2_doc_title,
                                page_start=cb.page_start,
                                page_end=cb.page_end,
                                source_span=cb.source_span,
                                exact_quote=(
                                    f"Clause {cb.clause_identifier or ''}: "
                                    f"{cb.title}".strip()
                                ),
                                section=cb.clause_identifier or cb.title,
                            )
                        ],
                        lawyer_questions=[
                            f"How does the addition of '{cb.title or cb.category}' "
                            f"in Version 2 affect the agreement?"
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                    )
                )

        return findings

    @staticmethod
    def _map_category(raw_category: str | None) -> VersionDiffCategory:
        if not raw_category:
            return VersionDiffCategory.OTHER
        cat = raw_category.lower().strip()
        if "party" in cat or "parties" in cat:
            return VersionDiffCategory.PARTIES
        if "date" in cat or "term" in cat or "duration" in cat:
            return VersionDiffCategory.DATES
        if "oblig" in cat:
            return VersionDiffCategory.OBLIGATIONS
        if "notice" in cat or "terminat" in cat:
            return VersionDiffCategory.NOTICE
        if "pay" in cat or "fee" in cat or "rent" in cat or "price" in cat:
            return VersionDiffCategory.PAYMENT
        if "clause" in cat or "govern" in cat or "confidential" in cat:
            return VersionDiffCategory.CLAUSE
        return VersionDiffCategory.OTHER
