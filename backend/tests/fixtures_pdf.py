import io


def create_synthetic_pdf(pages_text: list[str]) -> bytes:
    """Generate a deterministic in-memory PDF byte stream with text per page."""
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")

    offsets: dict[int, int] = {}

    # 1 0 obj: Catalog
    offsets[1] = buffer.tell()
    buffer.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    num_pages = len(pages_text)
    page_ids = [4 + i * 2 for i in range(num_pages)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)

    # 2 0 obj: Pages
    offsets[2] = buffer.tell()
    pages_obj = (
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj\n"
    )
    buffer.write(pages_obj.encode("latin1"))

    # 3 0 obj: Font
    offsets[3] = buffer.tell()
    buffer.write(
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for i, text in enumerate(pages_text):
        pid = 4 + i * 2
        cid = 5 + i * 2

        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content = f"BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET".encode("latin1")

        offsets[cid] = buffer.tell()
        buffer.write(
            f"{cid} 0 obj\n<< /Length {len(stream_content)} >>\nstream\n".encode(
                "latin1"
            )
        )
        buffer.write(stream_content)
        buffer.write(b"\nendstream\nendobj\n")

        offsets[pid] = buffer.tell()
        page_dict = (
            f"{pid} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>\nendobj\n"
        )
        buffer.write(page_dict.encode("latin1"))

    startxref = buffer.tell()
    total_objects = 3 + num_pages * 2
    buffer.write(f"xref\n0 {total_objects + 1}\n".encode("latin1"))
    buffer.write(b"0000000000 65535 f \r\n")
    for obj_id in range(1, total_objects + 1):
        off = offsets[obj_id]
        buffer.write(f"{off:010d} 00000 n \r\n".encode("latin1"))

    buffer.write(
        f"trailer\n<< /Size {total_objects + 1} /Root 1 0 R >>\n"
        f"startxref\n{startxref}\n%%EOF\n".encode("latin1")
    )
    return buffer.getvalue()


def create_scanned_synthetic_pdf(page_count: int = 1) -> bytes:
    """Generate an in-memory PDF where pages have no native text (scanned)."""
    return create_synthetic_pdf([""] * page_count)
