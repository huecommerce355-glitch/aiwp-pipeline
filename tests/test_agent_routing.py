from test_manifest import load_manifest


def agent_routing():
    return load_manifest()["pipeline"]["agent_routing"]


def test_agent_routing_uses_capability_based_policy():
    assert agent_routing()["policy"] == "capability-based"


def test_agent_routing_rules_map_capabilities_to_agents():
    rules = agent_routing()["rules"]
    mapping = {rule["capability"]: rule["agent"] for rule in rules}

    assert mapping["implementation"] == "codex"
    assert mapping["code_review"] == "cursor"


def test_cursor_is_registered_when_auth_is_pending():
    cursor = next(agent for agent in agent_routing()["agents"] if agent["name"] == "cursor")

    assert cursor["production"] is True
    assert cursor["auth_status"] in {"logged_in", "needs_login"}
    assert cursor["auth_status"] != "unavailable"


def test_cursor_review_has_degraded_fallback():
    routing = agent_routing()
    cursor = next(agent for agent in routing["agents"] if agent["name"] == "cursor")
    review_rule = next(rule for rule in routing["rules"] if rule["capability"] == "code_review")

    assert "codex.review" in cursor["degraded_fallback"]
    assert "degraded_from: cursor" in cursor["degraded_fallback"]
    assert "codex.review" in review_rule["fallback"]
    assert "degraded_from: cursor" in review_rule["fallback"]
