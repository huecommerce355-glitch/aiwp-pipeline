# M0.1 acceptance gates

M0.1 必须逐门通过并记录 HACP 状态；任何一门失败都不能宣称流水线完成。

1. **测试全绿**：执行项目规定的测试命令，所有测试通过，失败项有明确处理结论。
2. **Hermes 零写**：本实现过程不由 Hermes 写入任何文件；所有 Skill 文件由 Codex 创建。
3. **零 git**：本阶段不执行 commit、push 或创建 PR；Git 状态可审计且未产生这些外部动作。
4. **报告沉淀**：S8 生成 execution-report，至少包含 summary、metrics、artifacts，并完成索引同步。
5. **HACP 日志完整**：S1-S8 每阶段均有包含阶段、gateway、输入/输出摘要、验证结果和状态的 HACP 日志。

## Reproducibility Check

使用完全相同的 `pipeline_manifest.yaml` 启动第二条流水线。应能解析同一模板和阶段 ID 顺序，按相同契约执行并得到可比较的阶段结果；运行编号、会话 ID、时间戳等实例字段可以不同。不能通过复制或修改流程逻辑来完成检查。

## Parallel Execution gate

并行验收还必须确认：请求数不超过 manifest 的 `max_parallel`；每个实例的 `trace_id` 唯一且贯穿 S1-S8；启用 `knowledge_write_lock` 时，S8 写入按锁串行化，锁冲突实例排队等待，超时则明确失败。

## Capability-based agent routing

`pipeline.agent_routing.policy` 为 `capability-based` 时，路由由 manifest 中的 capability → agent 规则声明，执行器不得把阶段与 agent 的绑定硬编码到 Skill 或调用方中。当前规则将 implementation/testing 分配给 `codex`，将 code_review 分配给 `cursor`。

`cursor` 的 `auth_status: needs_login` 只表示当前认证状态，不影响其 `production: true` 的生产注册。认证不可用时，review 必须按 manifest 的降级声明转发到 `codex.review`，并携带 `degraded_from: cursor`；这表示能力降级和来源可追踪，不表示 cursor 从注册表移除。
