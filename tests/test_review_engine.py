import importlib.util
import sys
from pathlib import Path

from test_manifest import load_manifest


ROOT = Path(__file__).parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quality_gate = load_module("quality_gate_review", ROOT / "scripts/quality_gate.py")
sys.modules["quality_gate"] = quality_gate
review_result = load_module("review_result_review", ROOT / "scripts/review_result.py")
sys.modules["review_result"] = review_result
review_engine = load_module("review_engine_review", ROOT / "scripts/review_engine.py")


GOOD = {name: 100 for name in quality_gate.WEIGHTS}


def test_quality_gate_decisions():
    assert quality_gate.evaluate(GOOD, [], []) ["decision"] == "PASS"
    assert quality_gate.evaluate({name: 70 for name in GOOD}, [], []) ["decision"] == "CONDITIONAL"
    assert quality_gate.evaluate({name: 50 for name in GOOD}, [], []) ["decision"] == "FAIL"
    assert quality_gate.evaluate(GOOD, [{"severity": "critical", "message": "unsafe"}], []) ["decision"] == "FAIL"


def request(**overrides):
    base = {
        "request_id": "req-1", "trace_id": "trace-1", "task_id": "task-1",
        "execution_agent": "codex", "scores": GOOD,
        "artifact": {"repo": "demo", "branch": "main", "files": ["a.py"], "diff_stats": {"files": 1}},
    }
    base.update(overrides)
    return base


def test_review_mode_primary_and_degraded():
    assert review_engine.dispatch_review(request(cursor_auth_status="logged_in"))["review_mode"] == "primary"
    degraded = review_engine.dispatch_review(request(cursor_auth_status="needs_login"))
    assert degraded["review_mode"] == "degraded"
    assert degraded["degraded_from"] == "cursor"


def test_schema_contains_required_fields_and_validates():
    result = review_engine.run_mock_review(request(cursor_auth_status="logged_in"))
    assert review_result.REQUIRED_FIELDS <= result.keys()
    assert result["review_mode"] == "primary"
    assert result["confidence"] in {"high", "medium", "low"}
    assert result["execution_agent"] == "codex"
    assert result["review_agent"] == "cursor"
    assert "degraded_from" not in result
    assert review_result.validate_review_result(result) == (True, [])


def test_mock_review_is_read_only(tmp_path):
    reviewed = tmp_path / "reviewed.py"
    reviewed.write_text("print('before')\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    review_engine.run_mock_review(request(repo_path=str(tmp_path)))
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_rework_rounds():
    failed = {"decision": "FAIL"}
    assert [review_engine.rework_decision(failed, round)["action"] for round in range(1, 4)] == ["continue"] * 3
    assert review_engine.rework_decision(failed, 4) == {"action": "escalate", "next_round": 4}


def test_manifest_declares_review_and_rework():
    stages = load_manifest()["pipeline"]["stages"]
    review = next(stage for stage in stages if stage["id"] == "S7")
    rework = next(stage for stage in stages if stage["id"] == "S7b")
    assert review["review"]["read_only"] is True
    assert review["review"]["review_agent"]["primary"] == "cursor"
    assert rework["rework"]["max_rounds"] == 3
