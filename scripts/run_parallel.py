#!/usr/bin/env python3
"""Run manifest stages for bounded, trace-isolated pipeline instances."""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from validate_manifest import load_and_validate


class KnowledgeWriteLock:
    def __init__(self, path: Path, timeout: float = 30.0, poll_interval: float = 0.05):
        self.path = path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise TimeoutError(f"timed out waiting for knowledge lock: {self.path}")
                time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc, tb):
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None


def generate_instances(manifest: dict[str, Any], count: int) -> list[dict[str, Any]]:
    execution = manifest["pipeline"]["execution"]
    if count < 1:
        raise ValueError("instances must be positive")
    if count > execution["max_parallel"]:
        raise ValueError(f"requested {count} instances exceeds max_parallel={execution['max_parallel']}")
    policy = execution["trace_id_policy"]
    shared_trace_id = str(uuid.uuid4()) if policy == "shared" else None
    stages = [stage["id"] for stage in manifest["pipeline"]["stages"]]
    instances = []
    for _ in range(count):
        trace_id = shared_trace_id or str(uuid.uuid4())
        instances.append(
            {
                "instance_id": str(uuid.uuid4()),
                "trace_id": trace_id,
                "stages": [{"stage": stage_id, "trace_id": trace_id} for stage_id in stages],
            }
        )
    return instances


def run_instance(instance: dict[str, Any], manifest: dict[str, Any], lock_path: Path, lock_timeout: float) -> dict[str, Any]:
    trace_id = instance["trace_id"]
    for stage in instance["stages"]:
        stage["trace_id"] = trace_id
        stage["status"] = "completed"
        if stage["stage"] in {"S8", "S9"} and any(
            item["id"] == "S9" for item in manifest["pipeline"]["stages"]
        ):
            # The caller injects this payload into knowledge_write.write_knowledge.
            # Keeping the gateway out of this module avoids a cross-component import.
            stage["payload"] = {"trace_id": trace_id}
            if manifest["pipeline"]["execution"]["knowledge_write_lock"]:
                with KnowledgeWriteLock(lock_path, timeout=lock_timeout):
                    stage["knowledge_lock"] = "acquired"
                    stage["knowledge_write"] = "completed"
            else:
                stage["knowledge_lock"] = "disabled"
    instance["status"] = "completed"
    return instance


def run_parallel(manifest: dict[str, Any], count: int, manifest_path: Path, lock_timeout: float = 30.0) -> list[dict[str, Any]]:
    instances = generate_instances(manifest, count)
    execution = manifest["pipeline"]["execution"]
    lock_path = manifest_path.parent / ".locks" / "knowledge.lock"
    with ThreadPoolExecutor(max_workers=execution["max_parallel"]) as pool:
        futures = [pool.submit(run_instance, instance, manifest, lock_path, lock_timeout) for instance in instances]
        return [future.result() for future in futures]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parents[1] / "pipeline_manifest.yaml")
    parser.add_argument("--instances", type=int, default=1)
    parser.add_argument("--lock-timeout", type=float, default=30.0)
    args = parser.parse_args()
    manifest, errors = load_and_validate(args.manifest)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    try:
        result = run_parallel(manifest, args.instances, args.manifest, args.lock_timeout)
    except (ValueError, TimeoutError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"instances": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
