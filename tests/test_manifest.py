from pathlib import Path

import yaml


MANIFEST_PATH = Path(__file__).parents[1] / "pipeline_manifest.yaml"


def load_manifest():
    with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
        return yaml.safe_load(manifest_file)


def test_manifest_schema():
    manifest = load_manifest()
    pipeline = manifest["pipeline"]

    assert isinstance(pipeline["name"], str)
    assert isinstance(pipeline["version"], str)
    assert isinstance(pipeline["protocol"], dict)
    assert pipeline["protocol"]["name"] == "HACP"
    assert isinstance(pipeline["protocol"]["version"], str)

    stages = pipeline["stages"]
    assert len(stages) == 8
    assert [stage["id"] for stage in stages] == [f"S{i}" for i in range(1, 9)]
    assert len({stage["id"] for stage in stages}) == len(stages)

    templates = {template["id"]: template for template in pipeline["templates"]}
    assert "standard" in templates
    stage_ids = {stage["id"] for stage in stages}
    assert set(templates["standard"]["stages"]).issubset(stage_ids)

