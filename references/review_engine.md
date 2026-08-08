# Review Engine v1.4

## S7 / S7b flow

After S6 verification, S7 receives artifacts, test results, and diff statistics. It resolves the `code_review` capability from `pipeline.agent_routing`: Cursor is primary; when its declared authentication status is `needs_login`, the request is sent to `codex.review` in degraded mode with `degraded_from: cursor`. S7 emits a Review Result.

If the quality gate returns `PASS`, the pipeline proceeds to S8. A `CONDITIONAL` result is recorded for human visibility. A `FAIL` result enters S7b, which returns the task to the Codex execution agent. The loop permits rounds 1–3; a failure at round 4 escalates to `human`.

## Quality gate

`quality_gate.evaluate` computes a weighted average: correctness 30%, test coverage 20%, maintainability 20%, security 15%, and convention 15%. A score below 60 or any critical blocker produces `FAIL`. A score from 60 through 79, or any warning, produces `CONDITIONAL`. A score of at least 80 with no critical blocker produces `PASS`.

## Review Result Schema v1.0

The result contains identity (`review_id`, `request_id`, `trace_id`, `task_id`), routing (`review_mode`, `execution_agent`, `review_agent`, and `degraded_from` when degraded), confidence, artifact metadata (`repo`, `branch`, `files`, `diff_stats`), scores, gate decision, findings, blockers, and `rework_round`. `validate_review_result` checks required fields and routing invariants.

## Read-only and mock constraints

The mock review agent only reads values already present in the request and constructs an in-memory result. It does not invoke Cursor, write files, apply patches, run a formatter, or alter the reviewed repository. A production agent adapter may be added later behind the same dispatch contract.
