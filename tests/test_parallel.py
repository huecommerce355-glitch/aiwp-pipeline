import importlib.util
import sys
import threading
import time
from pathlib import Path

import pytest

from test_manifest import load_manifest


ROOT = Path(__file__).parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module("validate_manifest", ROOT / "scripts/validate_manifest.py")
sys.modules["validate_manifest"] = validator
parallel = load_module("run_parallel", ROOT / "scripts/run_parallel.py")


def test_execution_validation():
    manifest = load_manifest()
    assert validator.validate_manifest(manifest) == []
    execution = manifest["pipeline"]["execution"]
    for field, value in (("max_parallel", 0), ("max_parallel", -1), ("max_parallel", True)):
        execution[field] = value
        assert any("max_parallel" in error for error in validator.validate_manifest(manifest))
        execution[field] = 2
    execution["trace_id_policy"] = "invalid"
    assert any("trace_id_policy" in error for error in validator.validate_manifest(manifest))
    execution["trace_id_policy"] = "per-instance"
    execution["knowledge_write_lock"] = "true"
    assert any("knowledge_write_lock" in error for error in validator.validate_manifest(manifest))


def test_trace_ids_are_unique_and贯穿_stages():
    manifest = load_manifest()
    instances = parallel.generate_instances(manifest, 2)
    assert len({instance["trace_id"] for instance in instances}) == 2
    for instance in instances:
        assert {stage["trace_id"] for stage in instance["stages"]} == {instance["trace_id"]}


def test_knowledge_lock_serializes_waiters(tmp_path):
    lock_path = tmp_path / ".locks" / "knowledge.lock"
    entered = []
    second_acquired = threading.Event()

    def first():
        with parallel.KnowledgeWriteLock(lock_path, timeout=2):
            entered.append("first")
            time.sleep(0.15)

    def second():
        time.sleep(0.02)
        with parallel.KnowledgeWriteLock(lock_path, timeout=2):
            entered.append("second")
            second_acquired.set()

    first_thread = threading.Thread(target=first)
    second_thread = threading.Thread(target=second)
    first_thread.start()
    second_thread.start()
    first_thread.join()
    second_thread.join()
    assert second_acquired.is_set()
    assert entered == ["first", "second"]


def test_max_parallel_rejects_more_than_manifest_limit():
    with pytest.raises(ValueError, match="max_parallel"):
        parallel.generate_instances(load_manifest(), 3)
