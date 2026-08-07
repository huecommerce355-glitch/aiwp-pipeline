# aiwp-pipeline

AI Work Platform pipeline orchestration skill (v1.0). Manifest-driven S1-S8 stages.

## Pipeline Manifest

Stages are declared in pipeline_manifest.yaml (not hardcoded):

- S1 strategy.context.request
- S2 strategy.plan.generate
- S3 strategy.handoff (via hermes-orchestrator)
- S4 task.decompose
- S5 coding-agent.dispatch
- S6 verification
- S7 github.pr.lifecycle (REST)
- S8 knowledge.execution.write

Templates enable future pipeline variants.

## Tests

```bash
python3 -m pytest tests/ -v
```
