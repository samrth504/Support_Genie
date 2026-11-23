"""Load every ShopNest help doc from kb_docs/ into the knowledge base.

Run from the backend/ folder:
    python -m scripts.seed_kb            # adds docs that are not in the DB yet
    python -m scripts.seed_kb --force    # re-indexes ALL docs (after editing them)
"""
import argparse
import logging
import time
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.models.kb import KBDocument, KBStatus
from app.services.rag.ingest import index_document
from app.services.rag.loaders import extract_text, guess_title

KB_DIR = Path(__file__).resolve().parents[2] / "kb_docs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-index documents that already exist")
    args = parser.parse_args()
    setup_logging("INFO")
    log = logging.getLogger("seed_kb")

    files = sorted(p for p in KB_DIR.glob("*.md") if p.name.lower() != "readme.md")
    if not files:
        raise SystemExit(f"No .md files found in {KB_DIR}")

    t0 = time.time()
    total_chunks = 0
    with SessionLocal() as db:
        for path in files:
            text = extract_text(path.name, path.read_bytes())
            doc = db.scalar(select(KBDocument).where(KBDocument.filename == path.name))
            if doc and not args.force:
                log.info("skip  %-24s (already indexed, use --force to re-index)", path.name)
                continue
            if doc is None:
                doc = KBDocument(filename=path.name, title=guess_title(path.name, text), status=KBStatus.processing)
                db.add(doc)
                db.commit()
            else:
                doc.title = guess_title(path.name, text)
            n = index_document(db, doc, text)
            total_chunks += n
            log.info("ok    %-24s -> %2d chunks", path.name, n)

    log.info("Done: %d files, %d chunks in %.1fs", len(files), total_chunks, time.time() - t0)


if __name__ == "__main__":
    main()
