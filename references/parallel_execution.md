# Parallel execution

v1.1 adds bounded parallel execution as a manifest concern. `pipeline.execution.max_parallel` is the maximum number of instances accepted by the conservative runner; the current implementation uses a bounded `ThreadPoolExecutor`, not a durable worker pool.

Each instance has its own instance ID, progress records, and UUID `trace_id`. The trace ID is copied into every stage record, making interleaved HACP output attributable without sharing mutable instance state. `trace_id_policy: shared` remains valid for compatibility, but `per-instance` is the default manifest policy.

## S8 trace continuity

For S8 (`knowledge.execution.write`), `run_instance` adds the instance trace to the stage result as `stage["payload"]["trace_id"]`. The runner intentionally does not import `knowledge_write`: the caller that invokes `knowledge-gateway v1.2` must merge this payload into the write call, for example:

```python
knowledge_write.write_knowledge(
    project_id=project_id,
    report_data=report_data,
    **s8_stage["payload"],
)
```

This produces `trace_id=instance["trace_id"]` at the gateway boundary. With `trace_id_policy: per-instance`, parallel instances therefore retain isolated S8 trace continuity. The payload is invocation metadata only; it does not expand the S8 rule against writing raw content.

When `knowledge_write_lock` is enabled, an instance acquires an exclusive OS file lock at `.locks/knowledge.lock` immediately before S8 and releases it after the knowledge write. Other instances block by polling until the lock is released; a bounded timeout turns a stuck lock into an explicit failure. The lock serializes only the knowledge write, so unrelated stages can continue concurrently.

Future worker-pool evolution can replace the in-process executor with durable queues, leases, retries, and crash recovery while retaining the manifest contract, per-instance trace identity, and S8 lock boundary.
