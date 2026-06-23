"""
Document handling (the diagram's "PDF Parsing" step + the RAG knowledge base).

In production, buyer/regulatory requirements arrive as PDFs. `parse_requirements()`
is the seam for that: if a real parser (e.g. pypdf) and a PDF are wired in it would
run here; for the offline scaffold it returns the already-structured JSON that
`data/generate.py` produced. The knowledge-base loader feeds the RAG advisor.
"""
from __future__ import annotations

from ..data import loaders


def parse_requirements() -> dict:
    """
    Return per-country buyer requirements.

    Seam for real PDF parsing: drop in pypdf/pdfplumber here to extract MRLs,
    certifications and tariffs from buyer documents. The offline build returns
    the structured JSON that represents the parsed output.
    """
    return loaders.load_buyer_requirements()


def knowledge_base() -> dict[str, str]:
    """{filename: text} documents available to the RAG advisor."""
    return loaders.load_knowledge_base()
