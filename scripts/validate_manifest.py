#!/usr/bin/env python3
"""Validate an AIWP pipeline manifest and emit a machine-readable JSON result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REQUIRED_STAGE_FIELDS = {"id", "name", "gateway", "inputs", "outputs", "verification"}
TRACE_POLICIES = {"per-instance", "shared"}


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pipeline = manifest.get("pipeline") if isinstance(manifest, dict) else None
    if not isinstance(pipeline, dict):
        return ["pipeline must be a mapping"]

    execution = pipeline.get("execution")
    if not isinstance(execution, dict):
        errors.append("pipeline.execution must be a mapping")
    else:
        max_parallel = execution.get("max_parallel")
        if isinstance(max_parallel, bool) or not isinstance(max_parallel, int) or max_parallel <= 0:
            errors.append("pipeline.execution.max_parallel must be a positive integer")
        if execution.get("trace_id_policy") not in TRACE_POLICIES:
            errors.append("pipeline.execution.trace_id_policy must be per-instance or shared")
        if not isinstance(execution.get("knowledge_write_lock"), bool):
            errors.append("pipeline.execution.knowledge_write_lock must be boolean")

    stages = pipeline.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("pipeline.stages must be a non-empty list")
        stages = []
    stage_ids: list[str] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            errors.append(f"pipeline.stages[{index}] must be a mapping")
            continue
        missing = REQUIRED_STAGE_FIELDS - stage.keys()
        if missing:
            errors.append(f"pipeline.stages[{index}] missing: {', '.join(sorted(missing))}")
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id:
            errors.append(f"pipeline.stages[{index}].id must be a non-empty string")
        else:
            stage_ids.append(stage_id)
        for field in ("inputs", "outputs"):
            if field in stage and not isinstance(stage[field], list):
                errors.append(f"pipeline.stages[{index}].{field} must be a list")
        if "verification" in stage and (not isinstance(stage["verification"], str) or not stage["verification"].strip()):
            errors.append(f"pipeline.stages[{index}].verification must be non-empty")
    if len(stage_ids) != len(set(stage_ids)):
        errors.append("pipeline.stages ids must be unique")

    templates = pipeline.get("templates")
    if not isinstance(templates, list) or not templates:
        errors.append("pipeline.templates must be a non-empty list")
    else:
        template_ids: list[str] = []
        known_ids = set(stage_ids)
        for index, template in enumerate(templates):
            if not isinstance(template, dict):
                errors.append(f"pipeline.templates[{index}] must be a mapping")
                continue
            template_id = template.get("id")
            if not isinstance(template_id, str) or not template_id:
                errors.append(f"pipeline.templates[{index}].id must be a non-empty string")
            else:
                template_ids.append(template_id)
            template_stages = template.get("stages")
            if not isinstance(template_stages, list) or not template_stages:
                errors.append(f"pipeline.templates[{index}].stages must be a non-empty list")
            else:
                unknown = set(template_stages) - known_ids
                if unknown:
                    errors.append(f"pipeline.templates[{index}] references unknown stages: {', '.join(sorted(unknown))}")
        if len(template_ids) != len(set(template_ids)):
            errors.append("pipeline.templates ids must be unique")
    return errors


def load_and_validate(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        with path.open(encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        return None, [f"cannot read manifest: {exc}"]
    errors = validate_manifest(manifest)
    return manifest if not errors else manifest, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=Path(__file__).parents[1] / "pipeline_manifest.yaml")
    args = parser.parse_args()
    manifest, errors = load_and_validate(args.manifest)
    result = {"valid": not errors, "manifest": str(args.manifest), "errors": errors}
    if manifest and not errors:
        result["execution"] = manifest["pipeline"]["execution"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
