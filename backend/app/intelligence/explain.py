"""
Explainability helpers (the diagram's "Explainable AI (SHAP)" box).

Both the XGBoost readiness model (via native TreeSHAP) and the additive
opportunity score expose per-feature contributions. This module formats those
contributions into a single, UI-friendly shape so the frontend can render one
"why" component everywhere.
"""
from __future__ import annotations


def breakdown(feature_names, contributions, labels: dict | None = None) -> list[dict]:
    """
    Turn raw per-feature contributions into a sorted explanation list.

    Each item: {feature, label, contribution, direction}. Sorted by absolute
    impact so the strongest drivers come first.
    """
    labels = labels or {}
    items = [
        {
            "feature": name,
            "label": labels.get(name, name),
            "contribution": round(float(c), 3),
            "direction": "up" if c >= 0 else "down",
        }
        for name, c in zip(feature_names, contributions)
    ]
    items.sort(key=lambda d: abs(d["contribution"]), reverse=True)
    return items


def top_drivers(items: list[dict], k: int = 3) -> tuple[list[dict], list[dict]]:
    """Split into the strongest positive and negative drivers (each up to k)."""
    positives = [i for i in items if i["contribution"] > 0][:k]
    negatives = [i for i in items if i["contribution"] < 0][:k]
    return positives, negatives
