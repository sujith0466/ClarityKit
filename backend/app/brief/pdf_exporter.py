"""Deterministic, dependency-free in-memory PDF exporter for briefs."""

import io
from datetime import datetime

from app.brief.models import LawyerPreparationBrief


def _escape_pdf_text(text: str) -> str:
    """Escape special PDF text string characters (parentheses and backslashes)."""
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
        .replace("\n", " ")
    )


def _wrap_text(text: str, max_chars: int = 85) -> list[str]:
    """Simple greedy word-wrap on whitespace."""
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line: list[str] = []
    current_len = 0

    for word in words:
        if current_len + len(word) + (1 if current_line else 0) <= max_chars:
            current_line.append(word)
            current_len += len(word) + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)

    if current_line:
        lines.append(" ".join(current_line))

    return lines


class SimplePDFBuilder:
    """Minimal PDF 1.4 document builder producing standard compliant output."""

    def __init__(self, page_width: int = 612, page_height: int = 792) -> None:
        self.page_width = page_width
        self.page_height = page_height
        self.margin_x = 54  # 0.75 in
        self.margin_top = 54
        self.margin_bottom = 54
        self.cursor_y = page_height - self.margin_top
        self.pages: list[list[str]] = [[]]
        self.current_page_idx = 0

    def add_page(self) -> None:
        self.pages.append([])
        self.current_page_idx += 1
        self.cursor_y = self.page_height - self.margin_top

    def check_page_break(self, required_space: int = 20) -> None:
        if self.cursor_y - required_space < self.margin_bottom:
            self.add_page()

    def add_heading1(self, text: str) -> None:
        self.check_page_break(32)
        escaped = _escape_pdf_text(text)
        cmd = (
            f"BT /F2 16 Tf 0.08 0.12 0.25 rg "
            f"{self.margin_x} {self.cursor_y} Td ({escaped}) Tj ET"
        )
        self.pages[self.current_page_idx].append(cmd)
        self.cursor_y -= 22

    def add_heading2(self, text: str) -> None:
        self.check_page_break(24)
        escaped = _escape_pdf_text(text)
        cmd = (
            f"BT /F2 12 Tf 0.12 0.18 0.35 rg "
            f"{self.margin_x} {self.cursor_y} Td ({escaped}) Tj ET"
        )
        self.pages[self.current_page_idx].append(cmd)
        self.cursor_y -= 16

    def add_heading3(self, text: str) -> None:
        self.check_page_break(18)
        escaped = _escape_pdf_text(text)
        cmd = (
            f"BT /F2 10 Tf 0.2 0.25 0.35 rg "
            f"{self.margin_x} {self.cursor_y} Td ({escaped}) Tj ET"
        )
        self.pages[self.current_page_idx].append(cmd)
        self.cursor_y -= 14

    def add_paragraph(
        self,
        text: str,
        font: str = "/F1",
        font_size: int = 9,
        line_height: int = 12,
        max_chars: int = 85,
    ) -> None:
        lines = _wrap_text(text, max_chars=max_chars)
        for line in lines:
            self.check_page_break(line_height)
            escaped = _escape_pdf_text(line)
            cmd = (
                f"BT {font} {font_size} Tf 0.1 0.1 0.1 rg "
                f"{self.margin_x} {self.cursor_y} Td ({escaped}) Tj ET"
            )
            self.pages[self.current_page_idx].append(cmd)
            self.cursor_y -= line_height

    def add_bullet(self, text: str, max_chars: int = 80) -> None:
        line_height = 13
        lines = _wrap_text(text, max_chars=max_chars)
        for idx, line in enumerate(lines):
            self.check_page_break(line_height)
            escaped = _escape_pdf_text(line)
            bullet_prefix = "*  " if idx == 0 else "   "
            cmd = (
                f"BT /F1 9 Tf 0.15 0.15 0.15 rg "
                f"{self.margin_x + 10} {self.cursor_y} Td "
                f"({bullet_prefix}{escaped}) Tj ET"
            )
            self.pages[self.current_page_idx].append(cmd)
            self.cursor_y -= line_height

    def add_disclaimer_box(self, text: str) -> None:
        self.check_page_break(60)
        box_top = self.cursor_y
        box_width = self.page_width - (2 * self.margin_x)
        lines = _wrap_text(text, max_chars=78)
        box_height = (len(lines) * 12) + 24
        box_bottom = box_top - box_height

        # Draw light background box
        bg_cmd = (
            f"0.96 0.96 0.98 rg {self.margin_x} {box_bottom} "
            f"{box_width} {box_height} re f "
            f"0.8 0.8 0.85 RG 1 w {self.margin_x} {box_bottom} "
            f"{box_width} {box_height} re S"
        )
        self.pages[self.current_page_idx].append(bg_cmd)

        text_y = box_top - 16
        # Title
        cmd_title = (
            f"BT /F2 9 Tf 0.7 0.2 0.1 rg {self.margin_x + 12} {text_y} Td "
            f"(IMPORTANT NOTICE & LEGAL DISCLAIMER) Tj ET"
        )
        self.pages[self.current_page_idx].append(cmd_title)
        text_y -= 14

        for line in lines:
            escaped = _escape_pdf_text(line)
            cmd = (
                f"BT /F1 8 Tf 0.2 0.2 0.2 rg {self.margin_x + 12} {text_y} Td "
                f"({escaped}) Tj ET"
            )
            self.pages[self.current_page_idx].append(cmd)
            text_y -= 11

        self.cursor_y = box_bottom - 15

    def add_horizontal_rule(self) -> None:
        self.check_page_break(12)
        cmd = (
            f"0.85 0.85 0.85 RG 0.75 w {self.margin_x} {self.cursor_y} m "
            f"{self.page_width - self.margin_x} {self.cursor_y} l S"
        )
        self.pages[self.current_page_idx].append(cmd)
        self.cursor_y -= 12

    def build_bytes(self) -> bytes:
        """Compile PDF objects into binary PDF stream."""
        num_pages = len(self.pages)
        # Add footers to all pages
        for p_idx in range(num_pages):
            footer_text = (
                f"ClarityKit Legal Preparation Brief  |  Confidential  |  "
                f"Page {p_idx + 1} of {num_pages}"
            )
            escaped_footer = _escape_pdf_text(footer_text)
            footer_cmd = (
                f"BT /F1 8 Tf 0.5 0.5 0.5 rg {self.margin_x} 30 Td "
                f"({escaped_footer}) Tj ET"
            )
            self.pages[p_idx].append(footer_cmd)

        # PDF Object assembly
        output = io.BytesIO()
        output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        objects: list[int] = []

        def write_obj(content: bytes) -> int:
            pos = output.tell()
            obj_num = len(objects) + 1
            objects.append(pos)
            output.write(f"{obj_num} 0 obj\n".encode("latin1"))
            output.write(content)
            output.write(b"\nendobj\n")
            return obj_num

        # Obj 1: Catalog (will point to Obj 2 Pages)
        # Obj 2: Pages (will list page objs 3 to 2+num_pages)
        # Obj 3..: Content Streams and Page Objects
        # Font 1: Helvetica
        # Font 2: Helvetica-Bold

        font1_num = write_obj(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"
        )
        font2_num = write_obj(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>"
        )

        page_obj_nums: list[int] = []
        content_obj_nums: list[int] = []

        for p_idx in range(num_pages):
            stream_body = "\n".join(self.pages[p_idx]).encode("latin1", "replace")
            stream_obj = (
                f"<< /Length {len(stream_body)} >>\nstream\n".encode("latin1")
                + stream_body
                + b"\nendstream"
            )
            c_num = write_obj(stream_obj)
            content_obj_nums.append(c_num)

        # Create Pages catalog placeholder index
        pages_dict_idx = len(objects) + 1
        # Now create Page objects
        for p_idx in range(num_pages):
            page_obj = (
                f"<< /Type /Page /Parent {pages_dict_idx} 0 R "
                f"/MediaBox [0 0 {self.page_width} {self.page_height}] "
                f"/Contents {content_obj_nums[p_idx]} 0 R "
                f"/Resources << /Font << /F1 {font1_num} 0 R "
                f"/F2 {font2_num} 0 R >> >> >>"
            ).encode("latin1")
            p_num = write_obj(page_obj)
            page_obj_nums.append(p_num)

        # Pages collection object
        kids_str = " ".join([f"{p} 0 R" for p in page_obj_nums])
        pages_obj = (
            f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>"
        ).encode("latin1")
        pages_obj_num = write_obj(pages_obj)

        # Catalog object
        catalog_obj = f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>".encode(
            "latin1"
        )
        catalog_obj_num = write_obj(catalog_obj)

        # Xref table
        xref_pos = output.tell()
        output.write(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
        output.write(b"0000000000 65535 f \n")
        for pos in objects:
            output.write(f"{pos:010d} 00000 n \n".encode("latin1"))

        # Trailer
        trailer = (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj_num} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("latin1")
        output.write(trailer)

        return output.getvalue()


def generate_brief_pdf(brief: LawyerPreparationBrief) -> bytes:
    """Generate a clean, professional, evidence-grounded PDF for the brief."""
    builder = SimplePDFBuilder()

    # Document Header
    builder.add_heading1("CLARITYKIT — LAWYER PREPARATION BRIEF")
    builder.add_paragraph(f"Title: {brief.title}", font="/F2")
    builder.add_paragraph(f"Document ID: {brief.document_id}")
    if isinstance(brief.created_at, datetime):
        gen_time = brief.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        gen_time = str(brief.created_at)[:19].replace("T", " ") + " UTC"
    builder.add_paragraph(f"Generated: {gen_time}")
    builder.add_paragraph(f"Completeness Score: {int(brief.completeness_score * 100)}%")
    builder.add_horizontal_rule()

    # Prominent Legal Disclaimer
    disclaimer_text = brief.disclaimer or (
        "IMPORTANT NOTICE: This preparation brief is an evidence-grounded aid "
        "designed to help you prepare for consultation with a qualified legal "
        "professional. It does NOT constitute legal advice, legal opinions, or "
        "recommendations. Only a qualified attorney can provide legal advice "
        "for your specific jurisdiction and situation."
    )
    builder.add_disclaimer_box(disclaimer_text)

    # Executive Summary / Situation Summary
    exec_summary = brief.situation_summary
    if exec_summary:
        builder.add_heading2("1. Executive Summary")
        builder.add_paragraph(exec_summary)
        builder.cursor_y -= 6

    # Sections in brief
    sections_list = (
        list(brief.sections.values())
        if isinstance(brief.sections, dict)
        else list(brief.sections)
    )
    section_num = 2
    for section in sections_list:
        if not section.items:
            continue
        builder.add_heading2(f"{section_num}. {section.title}")
        if section.description:
            builder.add_paragraph(section.description)

        for item in section.items:
            citation_str = ""
            if item.page_start:
                if item.page_end and item.page_end != item.page_start:
                    citation_str = f" [pp. {item.page_start}-{item.page_end}]"
                else:
                    citation_str = f" [p. {item.page_start}]"

            trust_badge = (
                f" ({item.trust_tier.value})"
                if hasattr(item, "trust_tier") and item.trust_tier
                else ""
            )
            item_title = item.title or item.text or "Item"
            item_content = item.content or item.text or ""
            item_text = (
                f"{item_title}{citation_str}{trust_badge}: {item_content}"
                if item_content != item_title
                else f"{item_title}{citation_str}{trust_badge}"
            )
            builder.add_bullet(item_text)

            if item.source_span:
                # Add evidence excerpt indent
                short_span = item.source_span[:160] + (
                    "..." if len(item.source_span) > 160 else ""
                )
                builder.add_bullet(f'Evidence excerpt: "{short_span}"', max_chars=75)

        builder.cursor_y -= 8
        section_num += 1

    # Questions for Legal Professional
    if brief.questions_for_lawyer:
        builder.add_heading2(f"{section_num}. Questions for Your Legal Professional")
        builder.add_paragraph(
            "Use these neutral, document-grounded questions during consultation:"
        )
        for q in brief.questions_for_lawyer:
            category_tag = f"[{q.category.upper()}] " if q.category else ""
            clause_tag = f" (Ref: {q.related_clause_id})" if q.related_clause_id else ""
            builder.add_bullet(f"{category_tag}{q.question}{clause_tag}")
            if q.rationale:
                builder.add_bullet(f"Rationale: {q.rationale}", max_chars=75)
        builder.cursor_y -= 8
        section_num += 1

    # Facts to Confirm
    if brief.facts_to_confirm:
        builder.add_heading2(f"{section_num}. Facts to Confirm with Attorney")
        for fact in brief.facts_to_confirm:
            builder.add_bullet(fact)
        builder.cursor_y -= 8
        section_num += 1

    # Documents to Bring
    if brief.documents_to_bring:
        builder.add_heading2(f"{section_num}. Documents to Bring to Consultation")
        for doc_item in brief.documents_to_bring:
            builder.add_bullet(doc_item)
        builder.cursor_y -= 8
        section_num += 1

    # Open Questions
    if brief.open_questions:
        builder.add_heading2(f"{section_num}. Open Questions & Ambiguities")
        for oq in brief.open_questions:
            builder.add_bullet(oq)
        builder.cursor_y -= 8

    return builder.build_bytes()
