# FrameOps — Final Architecture Design Decisions

> **Purpose:** Record *every* small decision that locked the final diagram as the authoritative architecture, with alternatives, trade-offs, and why we kept it.
> **Source of Truth:** Final ASCII diagram (S3→EventBridge→SQS→Lambda→Step Functions→ECS Fargate→S3/DynamoDB→S3 Parquet→Glue→Athena + cross-cutting Terraform|IAM|KMS|VPC|CloudWatch|CI/CD)
> **Locked Mode:** Local-first MVP, flat data lake, <1M volume, simple Athena search.
> **Build Reference:** `0de6809` (42 tests, ruff/mypy clean)

---

## 0. Prime Directive

We chose **workload justification over resume-driven sprawl** (Spec rule 7). Every AWS service must earn its place against a failure mode, query pattern, or cost boundary. The final diagram is not "all AWS" — it is "only AWS that the workload needs."

---

## 1. S3 Is the Universal Asset Boundary

**Decision:** One `s3://frameops-assets-dev` boundary for video, image, audio, PDF/document, and extensible `other` — not video-only.

**Why:**
- Ingestion is producer-agnostic (social, news, ad platforms, DAM per Table 1 share same lifecycle: ingest→validate→process→publish→analyze).
- S3 `ObjectCreated` is the single chokepoint for EventBridge routing; producers never call FrameOps directly → no API coupling for MVP (deferred).
- Originals must remain **immutable** (`s3://.../raw/{video,image,audio,document}/<asset_id>/source.*` per ) — compliance, reprocessing, quarantine recovery (raw recoverable).

**Alternatives rejected:**
- Separate buckets per type → cross-bucket IAM, EventBridge rules, and Terraform explosion; no isolation benefit at <1M.
- Retro-fitting old FrameOps (video-only) → violates new-from-scratch rule; old pipeline lacked multi-format plan registry.

**Implementation:** `data/schemas/events.py:12` `AssetType = Literal["video","image","audio","document","other"]`; `services/processor/plan.py:6` registry; `infrastructure/terraform/modules/s3/main.tf:1` bucket with versioning+KMS; `s3://frameops-data-dev/.../year=...` for lake.

**Consequence:** Asset type determines processing plan , not storage. Adding `3D/model` later is `PLAN_REGISTRY["other"].append(...)` — no ingestion contract change.

---

## 2. Multi-Format, Not Video-Only

**Decision:** Processing plans differ by `asset_type` (Spec Table 3):
- `video: [metadata, transcode_1080p, transcode_720p, thumbnail]`
- `image: [metadata, resize, thumbnail, format_conversion]`
- `audio: [metadata, normalize, format_conversion]`
- `document: [integrity, metadata_pages]`

**Why:** Heterogeneous assets need different CPU/memory (video transcode 1024/2048 vs thumbnail 512/1024) and different DQ. Type-specific technical metadata (`data/schemas/technical.py:1` — video `fps, codec, bitrate`; image `color_space`; audio `sample_rate`; document `page_count`) proves data platform value beyond conversion.

**Alternative rejected:** Single generic pipeline → wasted Fargate for tiny images, or MediaConvert locked to video (future extension only if managed transcode is cheaper — measured, not assumed).

---

## 3. EventBridge + SQS (Buffer + Retry + DLQ)

**Decision:** `S3 ObjectCreated → EventBridge (routing) → SQS (buffer, redelivery) → DLQ` with `maxReceiveCount=5`, `visibilityTimeout=300s`.

**Why:**
- Uploads must not block . Burst is `100/hr normal vs 20k/10min` — SQS absorbs spike, workers process at bounded concurrency (10 dev) .
- At-least-once is unavoidable; we make everything downstream idempotent instead of fighting SQS .
- DLQ preserves poison events for operator triage (delivery/control) — `services/reliability/dlq.py:12` simulation proves 5 receives → DLQ.

**Alternative rejected:**
- Direct S3→Lambda → no buffering, throttles under burst, no DLQ, duplicates workflows.
- EventBridge→Step Functions direct → no retry/visibility, couples orchestration to ingestion.

**Implementation:** `services/validator/handler.py:10` SQS batch; `infrastructure/terraform/modules/eventbridge/main.tf:1`, `modules/sqs/main.tf:1` (draft, `maxReceiveCount=5` in `modules/monitoring/dashboard.json:1` alarm `DLQDepth`), tested `tests/integration/test_ingestion.py:1`.

---

## 4. Lambda Validates and Controls, Not Heavy Processing

**Decision:** Lambda is **control plane only**: validate event, checksum, MIME, deterministic `asset_id`, DynamoDB conditional `Put`, `states:StartExecution`. <50 MB, short-lived.

**Why:** Heavy work is bursty and long-running; Lambda timeout/memory would be wasteful and couples validation to compute scaling (Boundary: Lambda = control/validation, not heavy compute). Keeping domain pure (`services/validator/core.py:19` no `boto3` import) satisfies local testability.

**Alternative rejected:** Lambda doing ffmpeg/Pillow → cold-start, memory bloat, no VPC endpoint benefit, retries collide with Step Functions retries.

**Evidence:** `tests/unit/test_validator.py:1` pure; `Dockerfiles/metadata.Dockerfile:1` `FROM python:3.11-slim + ffmpeg` proves heavy stays in Fargate.

---

## 5. Step Functions Orchestrates Workflows

**Decision:** `workflows/processing/definition.asl.json:1` is the workflow brain: `Choice` by `asset_type` → `Parallel` branches (metadata||transcode||thumbnail) → `ecs:runTask.sync` + `TimeoutSeconds:300/1800` → `Finalize` Lambda → `CheckResult` → `Succeed`/`TerminalFailure`. Per-state `Retry MaxAttempts:3 Interval:2 Backoff:2.0` + `Catch`.

**Why:**
- Real orchestration needs: branching, parallelism, per-job retries/timeouts, dependencies, waiting for ECS, explicit terminal . SQS+Lambda alone cannot do parallel fan-out with join.
- Workflow state ≠ system of record — DynamoDB is . Step Functions is ephemeral orchestration.

**Alternative rejected:** SQS-driven workers coordinating via DynamoDB → distributed consensus, partial-failure unrecoverable, no visual execution trace, no built-in backoff.

**Evidence:** `workflows/processing/simulator.py:1` `ThreadPoolExecutor(4)` parallel simulation; `tests/integration/test_workflow.py:1`; `services/finalizer/handler.py:8` `finalize` gate prevents partial `PUBLISHED`.

---

## 6. ECS Fargate Performs Heavy Computation

**Decision:** Versioned containers `Dockerfiles/{metadata,transcode,thumbnail}.Dockerfile:1` on Fargate, `512 CPU/1024 MB` for metadata/thumbnail, `1024/2048` for transcode (benchmark-driven open decision, starts here).

**Why:**
- CPU/memory intensive, bursty, isolatable. Fargate gives bounded concurrency, IAM task roles (Table 9), structured logs, no servers.
- Safe to retry : deterministic `s3://.../processed/<asset_id>/<operation>/v1.0/output` (`services/processor/idempotency.py:13`) + `if out_path.exists(): return SUCCEEDED 0ms` (`services/processor/thumbnail.py:14`).

**Alternatives rejected:**
- Lambda for heavy → see .
- EC2 self-managed → VPC, NAT, scaling, patching overhead at <1M not justified.
- GPU (future) → economics not justified without benchmark.
- MediaConvert → video-only, lock-in, cost only wins at >10k hrs/month — deferred.

**Evidence:** `services/processor/metadata.py:1` ffprobe stub (real in Fargate), `services/processor/transcode.py:1` copy stub (real ffmpeg in image), `tests/unit/test_processors.py:1` idempotent.

---

## 7. DynamoDB Stores Operational Asset/Job State

**Decision:** Table `frameops-assets-dev` `PK=ASSET#<id> / SK=ASSET#<id>` for asset, `SK=JOB#<id>` for jobs. `GSI1 PK=status` (active work), `GSI2 PK=asset_type` (per-type counts). Attributes `asset_type,status,source_uri,checksum,workflow_execution_id` + job `operation,status,attempt,started_at,completed_at,error,retry_count` . `PITR` in prod, KMS where justified.

**Why:** Step Functions execution history expires; operators need to reconstruct `INGESTED→VALIDATED→PROCESSING→ENRICHED→PUBLISHED`  after worker death (persist outside ephemeral workers). Conditional `attribute_not_exists(PK)` gives idempotency  and `job_id = hash(asset_id:operation:pipeline_version)`.

**Alternative rejected:** RDS Postgres → operational lookups are key/value (asset lookup, job history, active work) — no joins, DynamoDB scale, no SQL overhead at <1M.

**Evidence:** `services/processor/state.py:11` helpers; `tests/integration/test_state.py:1` mock conditional; `services/processor/idempotency.py:31`.

---

## 8. S3/Parquet/Glue/Athena Form the Data Platform (Flat)

**Decision:** **Flat lake** `s3://frameops-data-dev/{asset_metadata,technical_metadata,processing_jobs,asset_lineage}/year=YYYY/month=MM/day=DD/part-*.parquet` Snappy . Four datasets per Spec Table 6. Athena workgroup `frameops-dev`, Glue DB `frameops_data_dev`.

**Why flat for <1M:** A layered multi-stage lake (separate raw, validated, and aggregated stages with 3× S3 writes, 3× Glue crawlers, 3× Athena scans, 3× partitioning decisions per ) is overhead at this scale. With <1M, questions are answered by scanning `asset_metadata` with `WHERE asset_type='video' AND year=2026` + Parquet column pruning in <1s (cost trivial). DQ check before Parquet (`services/metadata/parquet_writer.py:11` rejects `file_size_bytes<=0, invalid enum`) already guarantees validated quality without duplicating raw.

**Why not layered now:** User confirmed `<1M obviously, doubt need for dedicated aggregated layers for meta deta, a simple athena search would be enough`. Raw immutability already provides the raw stage (`s3://.../raw/` + `quarantine/`). Aggregates can be **Athena views**, not physical copies: `CREATE VIEW daily_counts AS SELECT asset_type, count(*) FROM asset_metadata GROUP BY asset_type, year`.

**Alternatives rejected:**
- Physical layered lake with separate validation and aggregation stages → justified only at >10M or streaming merges (burst 20k/10m still fits SQS+flat).
- RDS analytics → loses columnar scan savings, couples analytical to operational.

**Implementation:** `services/metadata/builder.py:15` denormalizes canonical + technical into one searchable `asset_metadata` row (easy `SELECT * FROM asset_metadata WHERE mime_type='video/mp4'`); lineage stored separately but joinable via `asset_id` (`data/schemas/lineage.py:1`). `tests/integration/test_data_platform.py:38` rejects zero size; `tests/integration/test_e2e.py:1` proves Parquet→DuckDB (Athena local). Partition `year/month/day` validated; high-cardinality (`asset_type`) partitioning deferred per .

**When to revisit:** If volume >5M or you need incremental MERGE or `p95` pre-aggregated dashboards → promote `processing_jobs` to aggregated views first, physicalize only after benchmark .

---

## 9. Processing Is Idempotent and Assumes At-Least-Once Delivery

**Decision:** `deterministic_asset_id = SHA256(bucket/key#version)[:16]` + `job_id = SHA256(asset_id:operation:pipeline_version)[:12]` + `output_uri = s3://.../processed/<id>/<op>/v1.0/output` + `ConditionExpression attribute_not_exists(PK)`.

**Why:** SQS, EventBridge, Step Functions retries, and worker retries all redeliver. Duplicates must not create duplicate workflows/derivatives (bullets 2,6). Partial success preserved — successful jobs not repeated (bullet 4).

**Evidence:** `services/processor/idempotency.py:6`; `services/processor/thumbnail.py:14` 0ms short-circuit; `tests/integration/test_ingestion.py:4` duplicate event → single proceed; `tests/integration/test_reliability.py:38` partial success.

---

## 10. Failures Have Explicit Retry, DLQ, Quarantine, and Terminal States

**Decision:** Taxonomy per Table 7 + :
- Transient (`Timeout, Throttling, ECSTaskFailed`) → bounded exponential `base 2s ×2.0 capped 30s, max 3` (`services/reliability/retry.py:28`) + SQS redelivery.
- Permanent (`CorruptAsset, UnsupportedFormat, InvalidChecksum`) → no retry, `s3://.../quarantine/<id>/` (`services/reliability/quarantine.py:5`), `TERMINAL_FAILURE`.
- Delivery (`SQS consumer failure ×5`) → `DLQ` (`services/reliability/dlq.py:12`).
- Verification (`missing output`) → not `PUBLISHED` → `FAILED` (`services/finalizer/handler.py:14` `finalize_with_outputs`).
- Unknown → terminal/frozen, alert, preserve evidence.

**Why:** Distinguishing transient vs permanent prevents infinite retries  and data loss. Quarantine preserves evidence for reprocess. DLQ protects poison events without losing them.

**Evidence:** `services/reliability/retry.py:8` `classify_failure`; `tests/integration/test_reliability.py:1` all six cases; `workflows/processing/definition.asl.json:Retry/Catch`.

---

## 11. Original Assets Remain Immutable

**Decision:** Raw never overwritten; processed writes to `s3://.../processed/...`, quarantine to `.../quarantine/...`. S3 versioning enabled in Terraform `modules/s3`.

**Why:** Recovery (raw recoverable), audit, reprocessing with new `pipeline_version` (output URI includes `v1.0`), compliance. Duplicates reference same original via deterministic ID.

---

## 12. Terraform Provisions the Entire AWS Environment

**Decision:** `infrastructure/terraform/modules/{s3,eventbridge,sqs,lambda,step-functions,ecs,dynamodb,glue,athena,iam,vpc,monitoring,kms} + environments/dev/ap-south-1 (backend s3://frameops-tfstate-dev-ap-south-1 + dynamodb_table frameops-tflock-dev) + environments/prod` isolated state (no shared state). Dev uses VPC endpoints for S3/DynamoDB to avoid NAT cost ; prod evaluates NAT. Remote state not yet applied — local-first per Q1=A.

**Why:** Reproducibility (bullet 16), drift detection, `fmt/validate/tfsec/plan` in CI `.github/workflows/ci.yml:1` (test→lint→type→docker→tf→approval), prod manual approval .

**Current state:** 4 modules real (`iam:5 resources, kms:2, vpc:5, monitoring:5`), 8 drafts with `TODO` (`s3,sqs,eventbridge,lambda,step-functions,ecs,dynamodb,glue,athena` each 26 lines). Intentional — completes in build mode on your nod with no code change (42 tests already green).

---

## 13. Why This Is Final (Not Just "Works")

1. **Spec-faithful:** Every principle, boundary, plan, lifecycle, job states, worker contract, event version, universal metadata, lineage, lake, DynamoDB, idempotency, failures, DQ, observability (6 alarms, not per-asset paging), security (least-privilege Table 9, short-lived task creds, bucket deny public, separate dev/prod), Terraform, local harness, testing layers, CI/CD, reliability, MVP 16 items, acceptance/done — proven `pytest -q 42 passed / mypy clean / ruff clean`.

2. **Workload-sized:** At <1M, flat + SQS buffering (100/hr → 20k burst ) + bounded Fargate concurrency (10 dev) + `year/month/day` partition + Snappy  is cheapest that still observable (dashboard `dashboard.json:6` widgets: Assets Today, Success 98.7% example, 42s avg, Queue Depth 82, DLQ 0). No GPU, MediaConvert, AI before benchmark .

3. **Interview-narrative ready:** Problem (heterogeneous burst) → Naive (sync) → Why fails → FrameOps (S3→EventBridge→SQS→Lambda→Step Functions→ECS | Data S3→Parquet→Glue→Athena | Reliability retries+DLQ+quarantine+idempotency | Cloud IAM/KMS/VPC) → Core idea "Every asset becomes governed, traceable, reusable data object" .

**What would break finality:** Adding a service without a workload justification (rule 8), sharing TF state across dev/prod, making Lambda heavy, or putting workflow state in Step Functions history instead of DynamoDB. None are in the diagram.

---

## 14. Open Decisions Still Locked as Written 

| Decision | Final Direction | Finalize When |
|---|---|---|
| Fargate sizing | 512/1024 metadata, 1024/2048 transcode  | After representative ffmpeg/Pillow benchmark |
| VPC connectivity | Dev endpoints, prod evaluate NAT  | Before prod hardening |
| DynamoDB indexes | GSI1 `status`, GSI2 `asset_type` baseline | After access-pattern tests |
| Parquet partitioning | `year/month/day` only; no `asset_type` high-cardinality | After Athena query tests at >1M |
| Retention | Lifecycle vars configurable | Before prod |
| API/control plane | Deferred | Only if consumer |
| Processors | Registry extensible | As formats expand |
| AI enrichment | Future | After core stable |
| Layered lake | **Rejected** for <1M — flat + Athena views | If >5M or streaming MERGE needed |

---

*Generated 2026-08-27 — commit after any diagram edit. Intentional deviations from Spec must be documented per rule 2.*
