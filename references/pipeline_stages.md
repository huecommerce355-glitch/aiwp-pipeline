# Pipeline stages

每个阶段都应使用 HACP 消息传递，并在进入下一阶段前完成本阶段验证。示例中的 `...` 表示经策略允许的摘要，不代表可以跳过字段。

## S1 — strategy.context.request

- gateway: `chatgpt-strategy-gateway`
- inputs: `project_id`
- actions: 按 P0-P3 分级检索项目上下文；P0 为空时发出降级警告。
- outputs: `context_summary`
- verification: P0 非空或明确记录降级警告。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S1","gateway":"chatgpt-strategy-gateway","inputs":{"project_id":"..."},"outputs":{"context_summary":"..."},"verification":"passed|degraded"}`

## S2 — strategy.plan.generate

- gateway: `chatgpt-strategy-gateway`
- inputs: `goal`, `project_id`
- actions: 基于上下文生成战略计划；计划只在内存态流转，ADR 不自动落盘。
- outputs: `plan`
- verification: 计划含目标与成功标准。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S2","gateway":"chatgpt-strategy-gateway","inputs":{"goal":"...","project_id":"..."},"outputs":{"plan":"..."},"verification":"passed"}`

## S3 — strategy.handoff

- gateway: `chatgpt-strategy-gateway`
- inputs: `strategy_id`, `goal`, `priorities`, `success_criteria`, `constraints`
- actions: 完成 4 支柱验证，将任务转交 `hermes-orchestrator`；不得直连 `ai-development-manager`。
- outputs: `task_id`, `forwarded_to`
- verification: target/forwarded target 等于 `hermes-orchestrator`。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S3","gateway":"chatgpt-strategy-gateway","inputs":{"strategy_id":"..."},"outputs":{"task_id":"...","forwarded_to":"hermes-orchestrator"},"verification":"passed"}`

## S4 — task.decompose

- gateway: `ai-development-manager`
- inputs: `goal`
- actions: 将目标拆解为有依赖关系的子任务 DAG，给每个子任务定义验收条件。
- outputs: `subtasks`
- verification: 每个子任务可独立验收且 DAG 依赖可解析。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S4","gateway":"ai-development-manager","inputs":{"goal":"..."},"outputs":{"subtasks":["..."]},"verification":"passed"}`

## S5 — coding-agent.dispatch

- gateway: `coding-agent-gateway`
- inputs: `repo_path`, `task_spec`
- actions: 在 `workspace-write` 与 PTY 条件下 dispatch Codex 执行子任务。
- outputs: `artifacts`, `codex_session_id`
- verification: 产物存在且任务测试通过。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S5","gateway":"coding-agent-gateway","inputs":{"repo_path":"...","task_spec":"..."},"outputs":{"artifacts":["..."],"codex_session_id":"..."},"verification":"passed"}`

## S6 — verification

- gateway: `coding-agent-gateway`
- inputs: `artifacts`, `test_command`
- actions: 独立检查产物并复跑 pytest，不复用未经核实的 S5 结论。
- outputs: `verification_result`
- verification: pytest 全绿，且产物检查通过。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S6","gateway":"coding-agent-gateway","inputs":{"artifacts":["..."],"test_command":"pytest"},"outputs":{"verification_result":"passed"},"verification":"passed"}`

## S7 — github.pr.lifecycle

- gateway: `github-development-gateway`
- inputs: `repo`, `branch`, `files`
- actions: 通过 Git Data API 创建分支，通过 REST API 创建 PR，完成 squash merge。
- outputs: `pr_number`, `merge_sha`
- verification: `merge_state == merged`。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S7","gateway":"github-development-gateway","inputs":{"repo":"...","branch":"...","files":["..."]},"outputs":{"pr_number":1,"merge_sha":"..."},"verification":"passed"}`

## S8 — knowledge.execution.write

- gateway: `obsidian-knowledge-gateway`
- inputs: `project_id`, `report_data`
- actions: 写入 execution-report 的 summary、metrics、artifacts 并同步索引；过滤 raw 内容。
- outputs: `report_path`
- verification: 索引同步且报告不含 raw 内容。
- HACP 示例: `{"protocol":"HACP/1.0","stage":"S8","gateway":"obsidian-knowledge-gateway","inputs":{"project_id":"...","report_data":{"summary":"...","metrics":{},"artifacts":[]}},"outputs":{"report_path":"..."},"verification":"passed"}`
