#!/usr/bin/env python3
"""Read-only Review Engine dispatch, mock review, and rework decisions."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import yaml

from quality_gate import evaluate
from review_result import build_review_result


ROOT = Path(__file__).parents[1]


def _manifest() -> dict[str, Any]:
    with (ROOT / "pipeline_manifest.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def dispatch_review(request: dict) -> dict:
    routing = _manifest()["pipeline"]["agent_routing"]
    capability = request.get("capability", "code_review")
    rule = next(item for item in routing["rules"] if item["capability"] == capability)
    primary = rule["agent"]
    agents = {agent["name"]: agent for agent in routing["agents"]}
    auth_status = request.get("cursor_auth_status", agents[primary].get("auth_status"))
    primary_mode = primary == "cursor" and auth_status == "logged_in"
    review_agent = primary if primary_mode else "codex.review"
    result = {
        "type": "review.dispatch", "capability": capability,
        "review_mode": "primary" if primary_mode else "degraded",
        "review_agent": review_agent, "execution_agent": request.get("execution_agent", "codex"),
    }
    if not primary_mode:
        result["degraded_from"] = primary
    return result


def run_mock_review(request: dict) -> dict:
    """Construct a review result from supplied scores without touching artifacts."""
    gate = evaluate(request.get("scores", {}), request.get("blockers", []), request.get("warnings", []))
    dispatch = dispatch_review(request)
    result = build_review_result(
        review_id=request.get("review_id", str(uuid.uuid4())),
        request_id=request.get("request_id", str(uuid.uuid4())),
        trace_id=request.get("trace_id", str(uuid.uuid4())), task_id=request.get("task_id", "unknown"),
        review_mode=dispatch["review_mode"], confidence=request.get("confidence", "medium"),
        execution_agent=dispatch["execution_agent"], review_agent=dispatch["review_agent"],
        degraded_from=dispatch.get("degraded_from"),
        artifact=request.get("artifact", {"repo": "", "branch": "", "files": [], "diff_stats": {}}),
        scores=gate["scores"], total_score=gate["total_score"], decision=gate["decision"],
        findings=request.get("findings", []), blockers=gate["blockers"],
        rework_round=request.get("rework_round", 0),
    )
    result["type"] = "review.result"
    result["rule_applied"] = gate["rule_applied"]
    result["warnings"] = gate["warnings"]
    return result


def rework_decision(result: dict, round: int) -> dict:
    if result.get("decision") == "PASS":
        return {"action": "pass", "next_round": round}
    if round >= 4:
        return {"action": "escalate", "next_round": round}
    return {"action": "continue", "next_round": round + 1}
