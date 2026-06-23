"""
Compliance check + risk analysis (Readiness & Compliance module).

Evaluates a tea lot against each destination's buyer requirements (parsed in
processing.documents): pesticide MRL, moisture, minimum grade and mandatory
certifications. Produces a pass/fail checklist plus a 0-100 compliance-risk score
that also feeds the opportunity suitability model.
"""
from __future__ import annotations

from ..processing import documents

# Ceylon grades, finest -> coarsest. A lot satisfies a "min_grade" requirement
# when its grade is at least as fine (rank >= required rank).
GRADE_RANK = {"BOPF": 3, "BOP": 2, "OP": 1}


def default_lot() -> dict:
    """A representative Ceylon tea lot used when no specific shipment is given."""
    return {
        "grade": "BOPF",
        "moisture_pct": 6.2,
        "pesticide_ppm": 0.02,
        "certifications": ["ISO 22000", "Halal"],
        "packaging": "Foil 5kg",
    }


def _grade_ok(lot_grade: str, min_grade: str) -> bool:
    return GRADE_RANK.get(lot_grade, 0) >= GRADE_RANK.get(min_grade, 0)


def check(country: str, lot: dict | None = None, requirements: dict | None = None) -> dict:
    """Run every requirement check for one country and summarise the result."""
    lot = lot or default_lot()
    reqs = (requirements or documents.parse_requirements()).get(country)
    if reqs is None:
        return {"country": country, "passed": False, "checks": [], "error": "Unknown destination"}

    missing_certs = [c for c in reqs["required_certifications"] if c not in lot["certifications"]]
    checks = [
        {
            "requirement": "Pesticide residue (MRL)",
            "required": f"≤ {reqs['max_pesticide_ppm']} ppm",
            "actual": f"{lot['pesticide_ppm']} ppm",
            "ok": lot["pesticide_ppm"] <= reqs["max_pesticide_ppm"],
        },
        {
            "requirement": "Moisture content",
            "required": f"≤ {reqs['max_moisture_pct']} %",
            "actual": f"{lot['moisture_pct']} %",
            "ok": lot["moisture_pct"] <= reqs["max_moisture_pct"],
        },
        {
            "requirement": "Minimum grade",
            "required": reqs["min_grade"],
            "actual": lot["grade"],
            "ok": _grade_ok(lot["grade"], reqs["min_grade"]),
        },
        {
            "requirement": "Certifications",
            "required": ", ".join(reqs["required_certifications"]),
            "actual": ", ".join(lot["certifications"]) or "none",
            "ok": not missing_certs,
        },
    ]

    failed = [c for c in checks if not c["ok"]]
    passed = not failed
    # Risk: each failed mandatory check is severe; tariff adds a smaller penalty.
    risk = min(100.0, 30.0 * len(failed) + reqs["import_tariff_pct"] * 0.8)

    return {
        "country": country,
        "passed": passed,
        "checks": checks,
        "missing_certifications": missing_certs,
        "import_tariff_pct": reqs["import_tariff_pct"],
        "demand_outlook": reqs["demand_outlook"],
        "compliance_risk": round(risk, 1),
        "summary": (
            "All mandatory requirements met." if passed
            else f"{len(failed)} requirement(s) not met: "
                 + ", ".join(c["requirement"] for c in failed)
        ),
    }


def check_all(lot: dict | None = None) -> dict[str, dict]:
    """Compliance result for every known destination."""
    reqs = documents.parse_requirements()
    return {country: check(country, lot, reqs) for country in reqs}
