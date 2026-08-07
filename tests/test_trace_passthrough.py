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


validator = load_module("validate_manifest_trace", ROOT / "scripts/validate_manifest.py")
sys.modules["validate_manifest"] = validator
parallel = load_module("run_parallel_trace", ROOT / "scripts/run_parallel.py")


def s8_stage(instance):
    return next(stage for stage in instance["stages"] if stage["stage"] == "S8")


def test_s8_stage_payload_contains_instance_trace_id(tmp_path):
    manifest = load_manifest()
    instance = parallel.generate_instances(manifest, 1)[0]

    result = parallel.run_instance(instance, manifest, tmp_path / "knowledge.lock", lock_timeout=1)

    assert s8_stage(result)["payload"]["trace_id"] == result["trace_id"]


def test_parallel_s8_trace_ids_are_isolated(tmp_path):
    manifest = load_manifest()

    results = parallel.run_parallel(manifest, 2, tmp_path / "manifest.yaml", lock_timeout=1)

    trace_ids = [s8_stage(instance)["payload"]["trace_id"] for instance in results]
    assert len(set(trace_ids)) == 2
    assert all(trace_id == instance["trace_id"] for trace_id, instance in zip(trace_ids, results))


def test_s8_payload_can_construct_knowledge_write_kwargs(tmp_path):
    manifest = load_manifest()
    instance = parallel.generate_instances(manifest, 1)[0]
    result = parallel.run_instance(instance, manifest, tmp_path / "knowledge.lock", lock_timeout=1)
    s8 = s8_stage(result)

    captured = {}

    def mock_write_knowledge(**kwargs):
        captured.update(kwargs)

    mock_write_knowledge(project_id="project-1", report_data={"summary": "ok"}, **s8["payload"])

    assert captured["trace_id"] == instance["trace_id"]
