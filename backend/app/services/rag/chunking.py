"""Split a document into chunks for RAG, using LangChain text splitters.

Two-step strategy:
1. MarkdownHeaderTextSplitter -> split at '#' / '##' headings, so every chunk knows its section
   (used for citations like "Refunds and Returns Help > Refund timelines").
2. RecursiveCharacterTextSplitter -> long sections are cut further into ~800-character pieces
   with 100 characters of overlap, preferring paragraph / sentence boundaries.
"""
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.core.config import get_settings

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def split_text(text: str, title: str) -> list[Document]:
    settings = get_settings()
    by_heading = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=False).split_text(text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(by_heading)

    result: list[Document] = []
    for chunk in chunks:
        content = chunk.page_content.strip()
        if len(content) < 20:          # drop empty / heading-only fragments
            continue
        section = chunk.metadata.get("h3") or chunk.metadata.get("h2") or chunk.metadata.get("h1") or title
        result.append(Document(page_content=content, metadata={"title": title, "section": section}))
    return result
