#!/usr/bin/env python3
"""Evaluate the Review Engine quality gate."""

from __future__ import annotations

from typing import Any


WEIGHTS = {
    "correctness": 0.30,
    "test_coverage": 0.20,
    "maintainability": 0.20,
    "security": 0.15,
    "convention": 0.15,
}


def _is_critical(blocker: Any) -> bool:
    if isinstance(blocker, dict):
        return blocker.get("critical") is True or str(blocker.get("severity", "")).lower() == "critical"
    return "critical" in str(blocker).lower()


def evaluate(scores: dict, blockers: list, warnings: list) -> dict:
    """Return a deterministic decision and the inputs used to reach it."""
    scores = dict(scores or {})
    blockers = list(blockers or [])
    warnings = list(warnings or [])
    total_score = round(sum(float(scores.get(name, 0)) * weight for name, weight in WEIGHTS.items()), 2)
    critical = any(_is_critical(blocker) for blocker in blockers)

    if total_score < 60 or critical:
        decision = "FAIL"
        rule = "total_score < 60 or critical blocker present"
    elif total_score < 80 or warnings:
        decision = "CONDITIONAL"
        rule = "total_score is 60-79 or non-critical warnings present"
    else:
        decision = "PASS"
        rule = "total_score >= 80 and no critical blocker"
    return {
        "decision": decision,
        "total_score": total_score,
        "scores": scores,
        "blockers": blockers,
        "warnings": warnings,
        "rule_applied": rule,
    }
