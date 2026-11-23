"""Turn an uploaded file (bytes) into plain text. Supported: .md, .txt, .pdf"""
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}


class UnsupportedFileError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
    else:
        text = data.decode("utf-8", errors="replace")

    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise UnsupportedFileError("The file has no readable text (scanned PDFs are not supported).")
    return text


def guess_title(filename: str, text: str) -> str:
    """Use the first Markdown '# Heading' if there is one, else the file name."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:255]
    return Path(filename).stem.replace("_", " ").replace("-", " ").title()[:255]
