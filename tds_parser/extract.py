"""Optional PDF text extraction (requires the ``pypdf`` extra)."""
from __future__ import annotations

from typing import Tuple


def extract_text(path: str) -> Tuple[str, int]:
    """Return ``(text, page_count)`` for a PDF file.

    ``pypdf`` is an optional dependency: ``pip install tds-parser[pdf]``.
    """
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - depends on environment
        raise SystemExit(
            "PDF 解析需要 pypdf，请先安装：pip install \"tds-parser[pdf]\""
        )
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - a single bad page must not kill the run
            pages.append("")
    return "\n".join(pages), len(reader.pages)
