# Parallel execution

v1.1 adds bounded parallel execution as a manifest concern. `pipeline.execution.max_parallel` is the maximum number of instances accepted by the conservative runner; the current implementation uses a bounded `ThreadPoolExecutor`, not a durable worker pool.

Each instance has its own instance ID, progress records, and UUID `trace_id`. The trace ID is copied into every stage record, making interleaved HACP output attributable without sharing mutable instance state. `trace_id_policy: shared` remains valid for compatibility, but `per-instance` is the default manifest policy.

When `knowledge_write_lock` is enabled, an instance acquires an exclusive OS file lock at `.locks/knowledge.lock` immediately before S8 and releases it after the knowledge write. Other instances block by polling until the lock is released; a bounded timeout turns a stuck lock into an explicit failure. The lock serializes only the knowledge write, so unrelated stages can continue concurrently.

Future worker-pool evolution can replace the in-process executor with durable queues, leases, retries, and crash recovery while retaining the manifest contract, per-instance trace identity, and S8 lock boundary.
