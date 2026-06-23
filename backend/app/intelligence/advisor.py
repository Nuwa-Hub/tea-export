"""
Generative AI advisor (the diagram's "Generative AI advisor (LLM + RAG)" box).

Retrieval-Augmented Generation, offline by default:

  retrieve()  TF-IDF cosine search over the local knowledge base (processing.documents)
  generate()  weave the retrieved guidance with the computed numbers into a narrative

Generation has two backends behind one interface:
  * "template" (default, fully offline, deterministic) — composes the narrative from
    the facts + retrieved snippets.
  * "llm" — if config.USE_LLM is set, the `anthropic` SDK is installed and a key is
    present, the same grounded context is sent to the Claude API for nicer prose.
    Any failure transparently falls back to the template, so the app never breaks.
"""
from __future__ import annotations

from .. import config
from ..processing import documents


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def retrieve(query: str, k: int = 3) -> list[dict]:
    """Top-k knowledge-base documents most relevant to the query (TF-IDF cosine)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    kb = documents.knowledge_base()
    if not kb:
        return []
    names, texts = list(kb.keys()), list(kb.values())
    vec = TfidfVectorizer(stop_words="english")
    matrix = vec.fit_transform(texts + [query])
    sims = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    order = sims.argsort()[::-1][:k]
    return [
        {"source": names[i], "score": round(float(sims[i]), 3), "text": texts[i].strip()}
        for i in order
        if sims[i] > 0
    ]


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _query_from_context(ctx: dict) -> str:
    rec = ctx.get("recommendation", {})
    risk = ctx.get("storage_risk", {})
    return (
        f"export readiness {ctx.get('status', '')} best market {rec.get('country', '')} "
        f"storage risk {risk.get('level', '')} currency outlook compliance certification"
    )


def _template_narrative(ctx: dict, retrieved: list[dict]) -> str:
    rec = ctx.get("recommendation", {})
    risk = ctx.get("storage_risk", {})
    parts = []

    eri, status = ctx.get("eri"), ctx.get("status")
    parts.append(
        f"The Export Readiness Index is {eri}/100 ({status}). {ctx.get('readiness_action', '')}".strip()
    )

    if rec:
        drivers = ", ".join(d["label"].lower() for d in rec.get("positive_drivers", [])) or "balanced fundamentals"
        line = (f"The strongest opportunity is {rec['country']} "
                f"(suitability {rec['suitability']}/100), driven by {drivers}.")
        if rec.get("runner_up"):
            line += f" {rec['runner_up']} is the next-best alternative."
        if rec.get("compliance_passed") is False:
            line += " Note that the representative lot does not yet meet this market's mandatory requirements."
        parts.append(line)

    if risk:
        parts.append(f"Storage-risk outlook is {risk.get('level', '').lower()}: {risk.get('note', '')}")

    if retrieved:
        snippet = retrieved[0]["text"].split(". ")[0]
        parts.append(f"Guidance: {snippet}.")

    return " ".join(p for p in parts if p)


def _llm_narrative(ctx: dict, retrieved: list[dict]) -> str | None:
    """Route the grounded context through Claude. Returns None on any failure."""
    if not (config.USE_LLM and config.ANTHROPIC_API_KEY):
        return None
    try:
        import anthropic

        sources = "\n\n".join(f"[{r['source']}] {r['text']}" for r in retrieved)
        facts = _template_narrative(ctx, [])
        prompt = (
            "You are a tea-export decision advisor for Sri Lanka. Using ONLY the facts and "
            "reference notes below, write a concise (3-4 sentence) export recommendation. "
            "Do not invent numbers.\n\n"
            f"FACTS: {facts}\n\nREFERENCE NOTES:\n{sources}"
        )
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


def advise(ctx: dict) -> dict:
    """Produce the advisor narrative + its citations. Offline template by default."""
    retrieved = retrieve(_query_from_context(ctx))
    narrative = _llm_narrative(ctx, retrieved)
    generator = "llm" if narrative else "template"
    if narrative is None:
        narrative = _template_narrative(ctx, retrieved)
    return {
        "narrative": narrative,
        "generator": generator,
        "citations": [{"source": r["source"], "score": r["score"]} for r in retrieved],
    }
