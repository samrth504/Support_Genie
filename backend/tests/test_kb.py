"""Knowledge-base tests: loaders, chunking, upload pipeline, permissions.

A fake embedding model is used so tests are fast and need no model download.
Vector *search* needs PostgreSQL + pgvector, so it is verified against Neon with
`python -m scripts.rag_demo` instead of in this SQLite test-suite.
"""
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.rag import embeddings
from app.services.rag.chunking import split_text
from app.services.rag.loaders import UnsupportedFileError, extract_text, guess_title
from tests.conftest import login

DIM = get_settings().embedding_dim

SAMPLE_MD = """# Refunds Help

## Refund timelines
UPI refunds take 1-3 working days. Card refunds take 5-7 working days after the quality check.

## Non-returnable items
Innerwear, perishable items and personalised products cannot be returned.
"""


class FakeEmbedder:
    """Deterministic bag-of-words vectors: same words -> similar vectors."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * DIM
        for word in text.lower().split():
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
        return v

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    monkeypatch.setattr(embeddings, "get_embedder", lambda: FakeEmbedder())


@pytest.fixture
def staff_headers(client: TestClient, staff_user: dict) -> dict:
    return {"Authorization": f"Bearer {login(client, staff_user['email'], staff_user['password'])}"}


# ------------------------------------------------------------------ unit tests
def test_extract_text_markdown_and_title():
    text = extract_text("refunds.md", SAMPLE_MD.encode())
    assert "UPI refunds" in text
    assert guess_title("refunds.md", text) == "Refunds Help"
    assert guess_title("my_notes.txt", "no heading here") == "My Notes"


def test_extract_text_rejects_unsupported_and_empty():
    with pytest.raises(UnsupportedFileError):
        extract_text("virus.exe", b"MZ...")
    with pytest.raises(UnsupportedFileError):
        extract_text("empty.md", b"   \n  ")


def test_split_text_keeps_sections_and_size_limit():
    chunks = split_text(SAMPLE_MD, "Refunds Help")
    sections = {c.metadata["section"] for c in chunks}
    assert {"Refund timelines", "Non-returnable items"} <= sections
    assert all(len(c.page_content) <= get_settings().chunk_size for c in chunks)
    assert all(c.metadata["title"] == "Refunds Help" for c in chunks)


# ------------------------------------------------------------------ API tests
def test_kb_endpoints_require_staff(client: TestClient):
    assert client.get("/api/kb/documents").status_code == 401
    client.post("/api/auth/signup", json={"name": "Rahul", "email": "rahul@shopnest.com", "password": "Password123"})
    headers = {"Authorization": f"Bearer {login(client, 'rahul@shopnest.com', 'Password123')}"}
    assert client.get("/api/kb/documents", headers=headers).status_code == 403
    files = {"file": ("refunds.md", SAMPLE_MD.encode(), "text/markdown")}
    assert client.post("/api/kb/upload", files=files, headers=headers).status_code == 403


def test_upload_indexes_document(client: TestClient, staff_headers: dict):
    files = {"file": ("refunds.md", SAMPLE_MD.encode(), "text/markdown")}
    resp = client.post("/api/kb/upload", files=files, headers=staff_headers)
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "processing"
    assert resp.json()["title"] == "Refunds Help"

    # TestClient runs background tasks right after the response -> already indexed
    docs = client.get("/api/kb/documents", headers=staff_headers).json()
    assert len(docs) == 1
    assert docs[0]["status"] == "ready"
    assert docs[0]["chunk_count"] >= 2


def test_duplicate_and_unsupported_uploads(client: TestClient, staff_headers: dict):
    files = {"file": ("refunds.md", SAMPLE_MD.encode(), "text/markdown")}
    client.post("/api/kb/upload", files=files, headers=staff_headers)
    assert client.post("/api/kb/upload", files=files, headers=staff_headers).status_code == 409

    bad = {"file": ("photo.png", b"\x89PNG....", "image/png")}
    assert client.post("/api/kb/upload", files=bad, headers=staff_headers).status_code == 422


def test_failed_indexing_is_recorded(client: TestClient, staff_headers: dict, monkeypatch):
    class Broken:
        def embed_documents(self, texts):
            raise RuntimeError("embedding service down")

    monkeypatch.setattr(embeddings, "get_embedder", lambda: Broken())
    files = {"file": ("refunds.md", SAMPLE_MD.encode(), "text/markdown")}
    client.post("/api/kb/upload", files=files, headers=staff_headers)
    doc = client.get("/api/kb/documents", headers=staff_headers).json()[0]
    assert doc["status"] == "failed"
    assert "embedding service down" in doc["error"]


def test_delete_document(client: TestClient, staff_headers: dict):
    files = {"file": ("refunds.md", SAMPLE_MD.encode(), "text/markdown")}
    doc_id = client.post("/api/kb/upload", files=files, headers=staff_headers).json()["id"]
    assert client.delete(f"/api/kb/documents/{doc_id}", headers=staff_headers).status_code == 204
    assert client.get("/api/kb/documents", headers=staff_headers).json() == []
    assert client.delete(f"/api/kb/documents/{doc_id}", headers=staff_headers).status_code == 404
