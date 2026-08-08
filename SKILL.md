---
name: aiwp-pipeline
description: Use when orchestrating AI Work Platform pipelines with manifest-driven S1-S9 stages.
version: 1.4.0
author: OpenAI
license: MIT
platforms: [Codex, Hermes]
tags: [aiwp, pipeline, orchestration, HACP, workflow]
related_skills: [chatgpt-strategy-gateway, hermes-orchestrator, ai-development-manager, coding-agent-gateway]
---

# AIWP Pipeline

## Overview

AI Work Platform 流水线编排层：使用 manifest 驱动 S1-S9 执行，不把流程硬编码在 Skill 或调用方中。阶段可由模板组合，协议和验证点由 manifest 明确声明。

## How to Load

1. 读取本 Skill 根目录的 `pipeline_manifest.yaml`。
2. 根据请求选择 `templates` 中的模板；未指定时使用 `standard`。
3. 按模板列出的阶段顺序执行，并在每阶段记录完整 HACP 消息日志。
4. 每阶段只向声明的 gateway 转发声明的 inputs，检查 outputs 与 verification。
5. 执行 `references/acceptance_gates.md` 中的验收门，并记录结果。

阶段的具体输入、动作、输出、验证点和 HACP 示例见 [references/pipeline_stages.md](references/pipeline_stages.md)。

## 使用方式

将 `pipeline_manifest.yaml` 作为唯一流程声明：读取阶段 ID，解析 gateway、inputs、outputs 和 verification，然后将上下文传递给下一阶段。新增流程时添加模板并复用阶段定义；只有在阶段契约确实不同的时候才新增阶段。

每阶段 HACP 日志至少应包含 pipeline、stage、gateway、inputs 摘要、outputs 摘要、verification 结果和时间/状态。敏感或原始内容遵循对应 gateway 的安全策略。

## Agent Routing

`pipeline_manifest.yaml` 的 `pipeline.agent_routing` 以声明式方式定义 capability-based agent routing。`rules` 将阶段所需 capability 映射到 agent：S5 的 implementation 和 S6 的 testing 使用 `codex`，S7 的 code_review 使用 `cursor`。

Agent 的 `production: true` 表示该 agent 已注册为生产路由候选；`auth_status` 描述当前认证状态，不会将 agent 标记为不可用。若 `cursor` 未登录，review 请求按声明的 `fallback` 降级到 `codex.review`，并保留 `degraded_from: cursor`，以便调用方和日志识别降级来源。

## Review Engine (v1.4)

S7 是只读 Review Engine：通过 `code_review` capability 路由到 Cursor；Cursor 未登录时降级到 `codex.review` 并标注 `degraded_from: cursor`。第一阶段使用 mock review agent，根据请求提供的评分生成 Review Result，不调用 Cursor，也不修改 artifact 或代码文件。

Quality gate 使用 correctness 30%、test coverage 20%、maintainability 20%、security 15%、convention 15% 的加权平均：低于 60 或存在 critical blocker 为 `FAIL`，60–79 或有 warning 为 `CONDITIONAL`，否则为 `PASS`。S7b 对 FAIL 最多重工 3 轮，仍失败则升级 human。

## Parallel Execution

manifest 的 `pipeline.execution` 声明并行策略：`max_parallel` 限制同时运行的实例数，`trace_id_policy: per-instance` 为每条实例流水线分配独立 UUID，并将其贯穿所有阶段记录；`knowledge_write_lock: true` 要求实例进入 S9 前取得 `.locks/knowledge.lock`，写入完成后释放。当前实现采用保守的受限并发，不引入完整 worker pool；超出上限的实例请求会被拒绝。

## pipeline_manifest.yaml 说明

manifest 包含 `pipeline` 元数据、结构化 `protocol`、可扩展的 `stages` 和 `templates`。模板通过阶段 ID 引用既有阶段，不复制阶段定义；因此同一 manifest 可以被重复执行，也可以支持未来的不同 pipeline 模板。`acceptance.reproducibility_check` 要求用同一 manifest 重复执行第二条流水线。

## Trace Continuity

并行执行时，`trace_id_policy: per-instance` 为每个实例分配独立 trace ID，并贯穿所有阶段结果。S9 `knowledge.execution.write` 会在 stage 结果的 `payload.trace_id` 中携带实例 trace ID。调用方将该 payload 合并到 knowledge-gateway v1.2 的 `knowledge_write.write_knowledge` kwargs，即可完成 `trace_id` 的自动传递；runner 不直接导入跨组件的 `knowledge_write`。

## acceptance_gates.md 摘要

M0.1 包含五门：测试全绿、Hermes 零写、零 git、报告沉淀、HACP 日志完整；此外必须完成 Reproducibility Check，即第二条流水线使用同一 manifest 可重复执行。完整定义见 [references/acceptance_gates.md](references/acceptance_gates.md)。

## Common Pitfalls

- 不要把阶段顺序硬编码到 Skill 逻辑中；以 manifest 的模板引用为准。
- S2 计划保持内存态，ADR 不自动落盘。
- S3 必须经 `hermes-orchestrator`，不得直连 `ai-development-manager`。
- S9 只写 execution-report 的 summary/metrics/artifacts，不写 raw 内容。
- 不要把 verification 文本当作已完成的验证；必须实际执行并记录结果。
