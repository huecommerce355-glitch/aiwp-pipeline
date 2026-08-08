#!/usr/bin/env python3
"""Review Result Schema v1.0 construction and validation."""

from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "schema_version", "review_id", "request_id", "trace_id", "task_id",
    "review_mode", "confidence", "execution_agent", "review_agent", "artifact",
    "scores", "total_score", "decision", "findings", "blockers", "rework_round",
}
ARTIFACT_FIELDS = {"repo", "branch", "files", "diff_stats"}


def build_review_result(
    review_id: str,
    request_id: str,
    trace_id: str,
    task_id: str,
    review_mode: str,
    confidence: str,
    execution_agent: str,
    review_agent: str,
    artifact: dict,
    scores: dict,
    total_score: float,
    decision: str,
    findings: list | None = None,
    blockers: list | None = None,
    rework_round: int = 0,
    degraded_from: str | None = None,
) -> dict:
    result = {
        "schema_version": "1.0", "review_id": review_id, "request_id": request_id,
        "trace_id": trace_id, "task_id": task_id, "review_mode": review_mode,
        "confidence": confidence, "execution_agent": execution_agent,
        "review_agent": review_agent, "artifact": artifact, "scores": scores,
        "total_score": total_score, "decision": decision, "findings": list(findings or []),
        "blockers": list(blockers or []), "rework_round": rework_round,
    }
    if degraded_from is not None:
        result["degraded_from"] = degraded_from
    return result


def validate_review_result(result: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return False, ["result must be a mapping"]
    missing = REQUIRED_FIELDS - result.keys()
    errors.extend(f"missing field: {field}" for field in sorted(missing))
    if result.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if result.get("review_mode") not in {"primary", "degraded"}:
        errors.append("review_mode must be primary or degraded")
    if result.get("confidence") not in {"high", "medium", "low"}:
        errors.append("confidence must be high, medium, or low")
    if result.get("review_mode") == "degraded" and not result.get("degraded_from"):
        errors.append("degraded_from is required in degraded mode")
    if result.get("review_mode") == "primary" and "degraded_from" in result:
        errors.append("degraded_from is only valid in degraded mode")
    if not isinstance(result.get("artifact"), dict):
        errors.append("artifact must be a mapping")
    elif missing := ARTIFACT_FIELDS - result["artifact"].keys():
        errors.extend(f"missing artifact field: {field}" for field in sorted(missing))
    if not isinstance(result.get("scores"), dict):
        errors.append("scores must be a mapping")
    if not isinstance(result.get("findings"), list):
        errors.append("findings must be a list")
    if not isinstance(result.get("blockers"), list):
        errors.append("blockers must be a list")
    if result.get("decision") not in {"PASS", "CONDITIONAL", "FAIL"}:
        errors.append("decision must be PASS, CONDITIONAL, or FAIL")
    if isinstance(result.get("rework_round"), bool) or not isinstance(result.get("rework_round"), int):
        errors.append("rework_round must be an integer")
    return not errors, errors
