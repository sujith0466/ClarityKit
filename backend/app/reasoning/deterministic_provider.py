import re
from datetime import datetime

from app.reasoning.models import (
    QAReasoningRequest,
    RawAnswerClaim,
    RawExtractedClause,
    RawExtractedDate,
    RawExtractedObligation,
    RawExtractedParty,
    RawExtractedReviewFlag,
    RawExtractionResult,
    RawQAResult,
    ReasoningRequest,
)
from app.reasoning.provider import ExtractionLLMProvider

# Standard clause category keywords
CLAUSE_CATEGORIES = {
    "confidentiality": [
        "confidential",
        "nondisclosure",
        "non-disclosure",
        "proprietary",
    ],
    "termination": [
        "termination",
        "term and termination",
        "expiration",
        "cancellation",
    ],
    "payment": [
        "payment",
        "compensation",
        "fees",
        "rent",
        "price",
        "remuneration",
        "invoicing",
    ],
    "liability": ["liability", "limitation of liability", "damages", "disclaimer"],
    "indemnification": ["indemnif", "hold harmless", "defend and hold"],
    "intellectual_property": [
        "intellectual property",
        "ip rights",
        "work product",
        "inventions",
        "patent",
        "copyright",
    ],
    "non_compete": ["non-compete", "noncompete", "restrictive covenant", "restraint"],
    "non_solicit": ["non-solicit", "nonsolicitation", "solicitation"],
    "dispute_resolution": [
        "dispute",
        "arbitration",
        "mediation",
        "governing law",
        "jurisdiction",
        "venue",
    ],
    "notices": ["notice", "notices", "communication"],
    "severability": ["severability", "invalidity"],
    "representations": [
        "representations",
        "warranties",
        "representations and warranties",
    ],
}

# Date regex patterns
DATE_PATTERNS = [
    # ISO: 2026-01-15 or 2026/01/15
    (
        r"\b(\d{4})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b",
        "%Y-%m-%d",
    ),
    # US Month Day, Year: January 15, 2026
    (
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
        "%B %d %Y",
    ),
    # Day Month Year: 15 January 2026
    (
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
        "%d %B %Y",
    ),
]


class DeterministicStructuredExtractionProvider(ExtractionLLMProvider):
    """Deterministic, pattern-aware extraction provider for test and development.

    NOTE: This is NOT a neural Large Language Model. It uses rule-based parsing,
    regex heuristics, and modal verb extraction to provide fully deterministic,
    offline-capable structured extraction without external API dependencies.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic-test-provider"

    def extract_structured_data(self, request: ReasoningRequest) -> RawExtractionResult:
        parties: list[RawExtractedParty] = []
        clauses: list[RawExtractedClause] = []
        obligations: list[RawExtractedObligation] = []
        dates: list[RawExtractedDate] = []
        review_flags: list[RawExtractedReviewFlag] = []

        pages = request.pages
        if not pages:
            return RawExtractionResult(
                parties=[],
                clauses=[],
                obligations=[],
                dates=[],
                review_flags=[],
                provider_info={
                    "provider": self.provider_name,
                    "type": "deterministic",
                },
            )

        # 1. Extract Parties from initial pages (usually page 1 or 2)
        for page in pages:
            p_num = page.get("page_number", 1)
            p_text = page.get("text", "")
            if p_num <= 2:
                page_parties = self._extract_parties(p_text, p_num)
                for p in page_parties:
                    if not any(
                        ep.name.lower() == p.name.lower()
                        and ep.role.lower() == p.role.lower()
                        for ep in parties
                    ):
                        parties.append(p)

        # 2. Extract Clauses across all pages
        clause_map: dict[str, RawExtractedClause] = {}
        for page in pages:
            p_num = page.get("page_number", 1)
            p_text = page.get("text", "")
            page_clauses = self._extract_clauses(p_text, p_num)
            for c in page_clauses:
                if c.clause_identifier not in clause_map:
                    clause_map[c.clause_identifier] = c
                    clauses.append(c)

        # 3. Extract Obligations across all pages
        for page in pages:
            p_num = page.get("page_number", 1)
            p_text = page.get("text", "")
            page_obligations = self._extract_obligations(p_text, p_num, clauses)
            obligations.extend(page_obligations)

        # 4. Extract Important Dates across all pages
        for page in pages:
            p_num = page.get("page_number", 1)
            p_text = page.get("text", "")
            page_dates = self._extract_dates(p_text, p_num)
            for d in page_dates:
                if not any(
                    ed.raw_text == d.raw_text and ed.page_number == d.page_number
                    for ed in dates
                ):
                    dates.append(d)

        # 5. Extract Review Flags across all pages & clauses
        for page in pages:
            p_num = page.get("page_number", 1)
            p_text = page.get("text", "")
            page_flags = self._extract_review_flags(p_text, p_num, clauses)
            for f in page_flags:
                if not any(
                    ef.title == f.title and ef.page_start == f.page_start
                    for ef in review_flags
                ):
                    review_flags.append(f)

        return RawExtractionResult(
            parties=parties,
            clauses=clauses,
            obligations=obligations,
            dates=dates,
            review_flags=review_flags,
            provider_info={
                "provider": self.provider_name,
                "type": "deterministic",
                "rules_applied": len(clauses)
                + len(parties)
                + len(obligations)
                + len(dates),
            },
        )

    def _extract_parties(self, text: str, page_num: int) -> list[RawExtractedParty]:
        parties: list[RawExtractedParty] = []

        # Pattern 1: between [Name] ("Role") and [Name] ("Role")
        between_pattern = re.compile(
            r'between\s+([A-Z][A-Za-z0-9\s,\.\&]+?)(?:\s*(?:\(|,)\s*["“\']?([A-Za-z\s]+)["”\']?\s*(?:\)|,))?\s+and\s+([A-Z][A-Za-z0-9\s,\.\&]+?)(?:\s*(?:\(|,)\s*["“\']?([A-Za-z\s]+)["”\']?\s*(?:\)|,))?(?:\.|\;|\n|$)',
            re.IGNORECASE,
        )
        for match in between_pattern.finditer(text):
            span_text = match.group(0).strip()
            name1 = match.group(1).strip().strip(",")
            role1 = match.group(2).strip() if match.group(2) else "Party"
            name2 = match.group(3).strip().strip(",")
            role2 = match.group(4).strip() if match.group(4) else "Party"

            if len(name1) > 2 and len(name1) < 80:
                parties.append(
                    RawExtractedParty(
                        name=name1,
                        role=role1,
                        page_number=page_num,
                        source_span=span_text,
                    )
                )
            if len(name2) > 2 and len(name2) < 80:
                parties.append(
                    RawExtractedParty(
                        name=name2,
                        role=role2,
                        page_number=page_num,
                        source_span=span_text,
                    )
                )

        # Pattern 2: Key-Value style: Landlord: ... / Tenant: ...
        role_headers = [
            "Landlord",
            "Tenant",
            "Employer",
            "Employee",
            "Client",
            "Contractor",
            "Disclosing Party",
            "Receiving Party",
            "Buyer",
            "Seller",
            "Licensor",
            "Licensee",
            "Company",
            "Consultant",
            "Borrower",
            "Lender",
        ]
        for role in role_headers:
            kv_pattern = re.compile(
                rf"\b{re.escape(role)}\s*[:\-]\s*([A-Z][A-Za-z0-9\s,\.\&]+?)(?:\n|\;|\.|$)",
                re.IGNORECASE,
            )
            for match in kv_pattern.finditer(text):
                name = match.group(1).strip().strip(",")
                if 2 < len(name) < 80:
                    span_text = match.group(0).strip()
                    parties.append(
                        RawExtractedParty(
                            name=name,
                            role=role,
                            page_number=page_num,
                            source_span=span_text,
                        )
                    )

        return parties

    def _classify_category(self, title: str, text: str) -> str:
        combined = f"{title} {text}".lower()
        for cat, keywords in CLAUSE_CATEGORIES.items():
            for kw in keywords:
                if kw in combined:
                    return cat
        return "general"

    def _extract_clauses(self, text: str, page_num: int) -> list[RawExtractedClause]:
        clauses: list[RawExtractedClause] = []

        # Heading patterns (e.g. "Section 1. Confidentiality", "1. Rent Payment")
        clause_pattern = re.compile(
            r"(?m)^(?:(?:Section|Article|Clause)\s+)?"
            r"([0-9IVXLCDM]+(?:\.[0-9]+)*|\b[A-Z]\b)[\.:\-]\s*([^\n\r]+)$"
        )

        matches = list(clause_pattern.finditer(text))
        for i, match in enumerate(matches):
            ident = match.group(1).strip()
            title = match.group(2).strip()
            start_pos = match.start()

            # Find boundary of this clause section (either next heading or end of text)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)

            clause_body = text[start_pos:end_pos].strip()
            source_span = clause_body[:300]  # Representative span for source citation

            category = self._classify_category(title, clause_body)

            clauses.append(
                RawExtractedClause(
                    clause_identifier=f"Clause-{ident}",
                    title=title,
                    category=category,
                    text=clause_body,
                    page_start=page_num,
                    page_end=page_num,
                    source_span=source_span,
                )
            )

        # Fallback if no numbered headings found: split paragraphs by keyword
        if not clauses:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for idx, line in enumerate(lines):
                for cat, keywords in CLAUSE_CATEGORIES.items():
                    if any(
                        line.lower().startswith(kw) or line.lower().endswith(kw)
                        for kw in keywords
                    ):
                        clauses.append(
                            RawExtractedClause(
                                clause_identifier=f"Section-{idx + 1}",
                                title=line[:50],
                                category=cat,
                                text=line,
                                page_start=page_num,
                                page_end=page_num,
                                source_span=line[:200],
                            )
                        )
                        break

        return clauses

    def _extract_obligations(
        self,
        text: str,
        page_num: int,
        clauses: list[RawExtractedClause],
    ) -> list[RawExtractedObligation]:
        obligations: list[RawExtractedObligation] = []

        # Split text into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        modal_patterns = [
            (
                r"\b([A-Z][A-Za-z0-9\s]{2,25})\s+"
                r"(shall|must|agrees to|is required to|undertakes to)\s+([^.;]+)"
            ),
        ]

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            for pat in modal_patterns:
                match = re.search(pat, sentence_clean, re.IGNORECASE)
                if match:
                    obligor = match.group(1).strip()
                    duty_verb = match.group(2).strip()
                    duty_rest = match.group(3).strip()
                    full_duty = f"{duty_verb} {duty_rest}"

                    # Detect trigger / condition (e.g. "Upon termination")
                    trigger = None
                    trigger_match = re.search(
                        r"\b(upon\s+[^,]+|in the event of\s+[^,]+|"
                        r"if\s+[^,]+|prior to\s+[^,]+)",
                        sentence_clean,
                        re.IGNORECASE,
                    )
                    if trigger_match:
                        trigger = trigger_match.group(1).strip()

                    # Detect deadline (e.g. "within 30 days")
                    deadline = None
                    deadline_match = re.search(
                        r"\b(within\s+\d+\s+(?:days|months|business days)|"
                        r"on or before\s+[^,.;]+|by\s+no\s+later\s+than\s+[^,.;]+|"
                        r"monthly on the \d+(?:st|nd|rd|th)? day)",
                        sentence_clean,
                        re.IGNORECASE,
                    )
                    if deadline_match:
                        deadline = deadline_match.group(1).strip()

                    # Associate with nearby clause if applicable
                    related_clause = None
                    for c in clauses:
                        if c.page_start <= page_num <= c.page_end:
                            if sentence_clean in c.text:
                                related_clause = c.clause_identifier
                                break

                    obligations.append(
                        RawExtractedObligation(
                            obligor=obligor,
                            duty=full_duty,
                            trigger=trigger,
                            deadline=deadline,
                            page_start=page_num,
                            page_end=page_num,
                            source_span=sentence_clean,
                            related_clause_identifier=related_clause,
                        )
                    )

        return obligations

    def _extract_dates(self, text: str, page_num: int) -> list[RawExtractedDate]:
        dates: list[RawExtractedDate] = []

        # Find sentences containing dates
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            for pattern, date_fmt in DATE_PATTERNS:
                for match in re.finditer(pattern, sentence_clean, re.IGNORECASE):
                    raw_date_str = match.group(0).strip()
                    normalized: str | None = None

                    # Attempt normalization
                    try:
                        clean_match = re.sub(
                            r"(\d+)(st|nd|rd|th)", r"\1", raw_date_str
                        ).replace(",", "")
                        clean_match = re.sub(r"\s+", " ", clean_match).strip()
                        parsed = datetime.strptime(clean_match, date_fmt)
                        normalized = parsed.strftime("%Y-%m-%d")
                    except Exception:
                        normalized = None

                    # Determine date type and description
                    lower_sent = sentence_clean.lower()
                    date_type = "milestone_date"
                    desc = "Document date reference"

                    if (
                        "effective" in lower_sent
                        or "commencement" in lower_sent
                        or "start date" in lower_sent
                    ):
                        date_type = "effective_date"
                        desc = "Agreement effective or commencement date"
                    elif (
                        "terminat" in lower_sent
                        or "expir" in lower_sent
                        or "end date" in lower_sent
                    ):
                        date_type = "expiration_date"
                        desc = "Agreement termination or expiration date"
                    elif "renew" in lower_sent:
                        date_type = "renewal_deadline"
                        desc = "Agreement renewal or option notice date"
                    elif (
                        "pay" in lower_sent
                        or "rent" in lower_sent
                        or "fee" in lower_sent
                    ):
                        date_type = "payment_due_date"
                        desc = "Payment or invoice due date"
                    elif "notice" in lower_sent:
                        date_type = "notice_deadline"
                        desc = "Notice submission deadline"

                    dates.append(
                        RawExtractedDate(
                            date_type=date_type,
                            raw_text=raw_date_str,
                            normalized_date=normalized,
                            description=desc,
                            page_number=page_num,
                            source_span=sentence_clean,
                        )
                    )

        return dates

    def _extract_review_flags(
        self,
        text: str,
        page_num: int,
        clauses: list[RawExtractedClause],
    ) -> list[RawExtractedReviewFlag]:
        flags: list[RawExtractedReviewFlag] = []

        # 1. Non-compete / restrictive covenant flag
        if re.search(
            r"\b(non-compete|noncompete|restraint of trade)\b", text, re.IGNORECASE
        ):
            match = re.search(
                r"([^.!?]*\b(non-compete|noncompete|restraint of trade)\b[^.!?]*[.!?])",
                text,
                re.IGNORECASE,
            )
            span = (
                match.group(0).strip() if match else "Non-compete provision identified"
            )
            flags.append(
                RawExtractedReviewFlag(
                    flag_type="restrictive_covenant",
                    title="Restrictive Covenant (Non-Compete)",
                    description=(
                        "The document contains a restrictive covenant. Reviewing the "
                        "geographic scope, duration, and applicability under governing "
                        "law is advised."
                    ),
                    severity="medium",
                    page_start=page_num,
                    page_end=page_num,
                    source_span=span,
                )
            )

        # 2. Automatic renewal / tight notice lock-in
        auto_renewal_pat = r"\b(automatically renew|automatic renewal|auto-renew)\b"
        if re.search(auto_renewal_pat, text, re.IGNORECASE):
            match = re.search(
                rf"([^.!?]*{auto_renewal_pat}[^.!?]*[.!?])",
                text,
                re.IGNORECASE,
            )
            span = match.group(0).strip() if match else "Automatic renewal clause"
            flags.append(
                RawExtractedReviewFlag(
                    flag_type="renewal_lock_in",
                    title="Automatic Renewal Provision",
                    description=(
                        "The document includes an automatic renewal term. Note any "
                        "advance cancellation notice windows required to prevent "
                        "rollover."
                    ),
                    severity="medium",
                    page_start=page_num,
                    page_end=page_num,
                    source_span=span,
                )
            )

        # 3. Unilateral modification or termination
        unilateral_pat = (
            r"\b(sole discretion|at its sole option|unilaterally modify|"
            r"without prior notice)\b"
        )
        if re.search(unilateral_pat, text, re.IGNORECASE):
            match = re.search(
                rf"([^.!?]*{unilateral_pat}[^.!?]*[.!?])",
                text,
                re.IGNORECASE,
            )
            span = match.group(0).strip() if match else "Discretionary clause"
            flags.append(
                RawExtractedReviewFlag(
                    flag_type="unilateral_discretion",
                    title="Unilateral Discretion or Modification",
                    description=(
                        "One party holds unilateral discretion or modification "
                        "rights. Consider whether mutual consent or explicit notice "
                        "should apply."
                    ),
                    severity="low",
                    page_start=page_num,
                    page_end=page_num,
                    source_span=span,
                )
            )

        # 4. Ambiguous phrasing
        ambiguous_pat = (
            r"\b(reasonable satisfaction|reasonable efforts|best efforts|"
            r"time is of the essence)\b"
        )
        if re.search(ambiguous_pat, text, re.IGNORECASE):
            match = re.search(
                rf"([^.!?]*{ambiguous_pat}[^.!?]*[.!?])",
                text,
                re.IGNORECASE,
            )
            span = match.group(0).strip() if match else "Ambiguous phrasing"
            flags.append(
                RawExtractedReviewFlag(
                    flag_type="ambiguous_term",
                    title="Potentially Subjective Standard",
                    description=(
                        "Phrasing such as 'best efforts' or 'reasonable "
                        "satisfaction' may benefit from more objective definition "
                        "to avoid future ambiguity."
                    ),
                    severity="low",
                    page_start=page_num,
                    page_end=page_num,
                    source_span=span,
                )
            )

        return flags

    def generate_grounded_answer(self, request: QAReasoningRequest) -> RawQAResult:
        """Deterministically answer questions grounded in retrieved document chunks."""
        question_lower = request.question.lower().strip()
        chunks = request.context_chunks

        # Prompt injection detection in question
        if any(
            adv in question_lower
            for adv in [
                "ignore previous instructions",
                "disregard previous",
                "reveal system prompt",
                "show system instructions",
                "you are now an unfiltered",
                "jailbreak",
                "bypass rules",
                "ignore all rules",
                "developer mode",
            ]
        ):
            return RawQAResult(
                answer_text=(
                    "ClarityKit operates strictly as an evidence-grounded "
                    "assistant. System directives cannot be overridden by "
                    "user or document prompts. All inquiries must pertain to "
                    "the factual contents of the uploaded document."
                ),
                claims=[
                    RawAnswerClaim(
                        claim_text=(
                            "System directives cannot be overridden by user or "
                            "document prompts."
                        ),
                        claim_type="general_information",
                    )
                ],
                general_information="System directives are fixed and non-overridable.",
                requires_professional_review=False,
                provider_info={
                    "provider": self.provider_name,
                    "mode": "adversarial_guard",
                },
            )

        # Check if question is asking for legal advice
        legal_advice_terms = [
            "should i sign",
            "is this legal",
            "is this enforceable",
            "is it valid",
            "will i win",
            "can i sue",
            "court outcome",
            "legal advice",
            "enforceable",
            "enforceability",
            "legally valid",
            "validity",
            "legal counsel",
        ]
        is_advice_query = any(term in question_lower for term in legal_advice_terms)

        if not chunks:
            return RawQAResult(
                answer_text=(
                    "The provided document does not contain enough information to "
                    "answer this question."
                ),
                claims=[],
                requires_professional_review=is_advice_query,
                provider_info={
                    "provider": self.provider_name,
                    "status": "no_context",
                },
            )

        claims: list[RawAnswerClaim] = []
        answer_sentences: list[str] = []

        # 1. Governing Law / Jurisdiction
        if any(
            term in question_lower
            for term in ["governing law", "jurisdiction", "which state", "what law"]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(governing law|laws of|jurisdiction)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(laws of|governed by)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=(
                                f"Agreement is governed by laws specified in the "
                                f"contract: {span}"
                            ),
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(f"According to Page {pnum}, {span}")
                    break

        # 2. Termination / Notice
        if any(
            term in question_lower
            for term in [
                "terminate",
                "termination",
                "notice period",
                "how can either party terminate",
                "cancel",
                "days notice",
            ]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(terminate|termination|written notice|days['\s]*notice)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(terminate|written notice)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Termination terms: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(
                        f"The agreement specifies on Page {pnum}: {span}"
                    )
                    break

        # 3. Parties
        if any(
            term in question_lower
            for term in [
                "parties",
                "who signed",
                "who are the parties",
                "who entered",
                "provider",
                "client",
            ]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(entered into by|between|parties|provider|client|acme|beta)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(entered into|between)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Contracting parties identified: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(
                        f"On Page {pnum}, the agreement identifies the parties: {span}"
                    )
                    break

        # 4. Payment / Fees / Compensation
        if any(
            term in question_lower
            for term in [
                "payment",
                "fee",
                "compensation",
                "price",
                "pay",
                "cost",
                "invoice",
            ]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(payment|fee|invoice|compensation|dollar|\$)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(payment|fee|invoice|compensation|dollar|\$)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Payment terms: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(
                        f"Regarding payment, Page {pnum} states: {span}"
                    )
                    break

        # 5. Confidentiality / NDA
        if any(
            term in question_lower
            for term in [
                "confidential",
                "nda",
                "nondisclosure",
                "non-disclosure",
                "secret",
            ]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(confidential|proprietary|disclosure)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(confidential|proprietary|disclosure)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Confidentiality obligation: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(
                        f"Regarding confidentiality, Page {pnum} provides: {span}"
                    )
                    break

        # 6. Liability / Indemnity
        if any(
            term in question_lower
            for term in ["liability", "indemn", "damages", "cap", "limit"]
        ):
            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                if re.search(
                    r"\b(liability|indemnif|damages|cap)\b",
                    ctext,
                    re.IGNORECASE,
                ):
                    sentence_match = re.search(
                        r"([^.!?]*\b(liability|indemnif|damages|cap)\b[^.!?]*[.!?])",
                        ctext,
                        re.IGNORECASE,
                    )
                    span = (
                        sentence_match.group(0).strip()
                        if sentence_match
                        else ctext[:100]
                    )
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Liability terms: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(f"Page {pnum} addresses liability: {span}")
                    break

        # 7. Generic keyword / text fallback search
        if not claims:
            stopwords = {
                "what",
                "when",
                "where",
                "which",
                "who",
                "whom",
                "whose",
                "why",
                "how",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "if",
                "in",
                "on",
                "at",
                "to",
                "for",
                "with",
                "by",
                "about",
                "against",
                "this",
                "that",
                "these",
                "those",
            }
            query_words = [
                w
                for w in re.findall(r"\b\w+\b", question_lower)
                if w not in stopwords and len(w) > 2
            ]

            for chunk in chunks:
                ctext = chunk.get("chunk_text", chunk.get("text", ""))
                pnum = chunk.get("page_number", chunk.get("page_start", 1))
                ctext_lower = ctext.lower()
                matched_words = [w for w in query_words if w in ctext_lower]
                if matched_words:
                    pat = rf"([^.!?]*\b({'|'.join(matched_words)})\b[^.!?]*[.!?])"
                    match = re.search(pat, ctext, re.IGNORECASE)
                    span = match.group(0).strip() if match else ctext[:120].strip()
                    claims.append(
                        RawAnswerClaim(
                            claim_text=f"Relevant passage: {span}",
                            claim_type="document_fact",
                            page_start=pnum,
                            page_end=pnum,
                            source_span=span,
                        )
                    )
                    answer_sentences.append(f"According to Page {pnum}: {span}")
                    break

        if not claims:
            return RawQAResult(
                answer_text=(
                    "The provided document does not contain enough information to "
                    "answer this question."
                ),
                claims=[],
                requires_professional_review=is_advice_query,
                provider_info={
                    "provider": self.provider_name,
                    "status": "insufficient_facts",
                },
            )

        final_answer = " ".join(answer_sentences)
        if is_advice_query:
            final_answer += (
                " Note: This analysis is factual. Determining legal enforceability "
                "or advice requires review by a qualified legal professional."
            )

        return RawQAResult(
            answer_text=final_answer,
            claims=claims,
            general_information=(
                "General legal standards may vary by jurisdiction."
                if is_advice_query
                else None
            ),
            requires_professional_review=is_advice_query,
            provider_info={"provider": self.provider_name, "status": "success"},
        )
