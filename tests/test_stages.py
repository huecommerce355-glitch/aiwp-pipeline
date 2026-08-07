from test_manifest import load_manifest


REQUIRED_FIELDS = {"id", "name", "gateway", "inputs", "outputs", "verification"}


def test_stage_definitions_are_complete():
    for stage in load_manifest()["pipeline"]["stages"]:
        assert REQUIRED_FIELDS <= stage.keys()
        assert stage["inputs"]
        assert stage["outputs"]
        assert stage["verification"].strip()


def test_s3_forwarded_target_constraint():
    stage = next(stage for stage in load_manifest()["pipeline"]["stages"] if stage["id"] == "S3")
    assert "hermes-orchestrator" in stage["verification"]
    assert "ai-development-manager" in stage["verification"]
    assert "hermes-orchestrator" in stage["description"]


def test_s8_has_no_raw_constraint():
    stage = next(stage for stage in load_manifest()["pipeline"]["stages"] if stage["id"] == "S8")
    text = f"{stage['description']} {stage['verification']}".lower()
    assert "raw" in text
    assert "summary" in stage["description"]
    assert "metrics" in stage["description"]
    assert "artifacts" in stage["description"]
