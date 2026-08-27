# FrameOps — Architectural Design Document

**Date:** 2026-08-27
**Version:** 1.0
**Source of Truth:** `FrameOps_Master_Project_Specification_v1.docx` (50 sections, Verification PASS)
**Region (dev):** `ap-south-1`
**Mode:** Local-first MVP — Phases 0-4 + 7-8 locally with moto/DuckDB; Terraform modules drafted but not applied until explicit approval (Q1=A)
**Stack:** Python 3.11, ffmpeg/ffprobe, Pillow, pypdf, Pydantic v2, boto3, moto, pytest, ruff, mypy

---

## 1. Executive Summary

FrameOps is an AWS-native, event-driven media asset processing and data platform. S3 is the universal storage boundary for heterogeneous assets (video, image, audio, PDF/document, extensible). Ingestion is asynchronous (S3 → EventBridge → SQS → Lambda), orchestration is via Step Functions (branching, parallel, retries, timeouts), heavy compute runs in ECS Fargate, operational state lives in DynamoDB, analytical data is S3/Parquet/Glue/Athena, and cross-cutting concerns are IAM/KMS/VPC/CloudWatch/Terraform/CI/CD.

This doc translates the Master Spec into an implementable architecture with explicit module boundaries, contracts, failure handling, and a 16-phase roadmap.

---

## 2. Goals & Non-Goals

### Goals
- One S3 boundary for video/image/audio/PDF/other; asset type determines processing plan (§6, §10)
- Asynchronous event-driven ingestion with SQS buffering/DLQ
- Step Functions orchestrates; Fargate computes (§14-15)
- Idempotent asset/job processing under at-least-once delivery (§22)
- DynamoDB as operational system of record; analytical datasets separated (§6, §20)
- Parquet+Glue+Athena data lake; CloudWatch observability; Terraform IaC
- Local testability before AWS (§34)

### Non-Goals (MVP)
- Consumer social product, exhaustive format coverage, AI enrichment as dependency, enterprise UI, service sprawl for resume (§5.2)
- Optional Control Plane API (§28) — deferred unless consumer exists
- Multi-region, GPU, QuickSight — future extensions (§45)

---

## 3. Architecture Overview

```
Media Sources
    │
    ▼
S3 (raw/processed/quarantine + s3://frameops-data/*)  ── ObjectCreated
    │                                                        │
    ▼                                                        ▼
EventBridge ─────────────────────────────────────────────► SQS ──► DLQ
                                                             │
                                                             ▼
                                                    Lambda Validator
                                                  (lightweight, dedup,
                                                   DynamoDB + SFN start)
                                                             │
                                                             ▼
                                                    Step Functions
                                                  (plan selection,
                                                   Parallel branches,
                                                   ECS RunTask sync,
                                                   retries/timeouts,
                                                   Finalize gate)
                                                             │
                                        ┌────────────────────┼────────────────────┐
                                        ▼                    ▼                    ▼
                                   Metadata             Transcode            Thumbnail
                                   Fargate              Fargate              Fargate
                                        └────────────────────┼────────────────────┘
                                                             ▼
                                                        Finalizer
                                                  (verify outputs + DQ)
                                                             │
                                        ┌────────────────────┼────────────────────┐
                                        ▼                    ▼                    ▼
                                   S3 Processed        DynamoDB State      S3 Data Lake Parquet
                                                                             (asset_metadata,
                                                                              technical_metadata,
                                                                              processing_jobs,
                                                                              asset_lineage)
                                                                                     │
                                                                                     ▼
                                                                              Glue → Athena

Cross-cutting: IAM (least privilege) · KMS · VPC (Fargate private subnets) · CloudWatch (logs/metrics/alarms) · Terraform (modules + dev/prod state) · CI/CD
```

**Service responsibility boundaries** per §8 Table 2 are enforced: S3=storage, EventBridge=routing, SQS=reliability, Lambda=control, Step Functions=workflow, Fargate=compute, DynamoDB=state, Glue=catalog, Athena=analytics.

---

## 4. Component Design

### 4.1 Ingestion (S3 → EventBridge → SQS → Lambda)
- **S3 layout** (§19): `s3://frameops-assets/{raw/{video,image,audio,document}, processed/{...}, quarantine} ` + `s3://frameops-data/{asset_metadata,technical_metadata,processing_jobs,asset_lineage}/year=YYYY/month=MM/day=DD/`
- **EventBridge:** Rule on `aws.s3` + `Object Created` → SQS. Event version explicit (§16.1).
- **SQS:** Standard queue, visibility timeout 300s, `maxReceiveCount=5` → DLQ, exponential redrive. Prevents blocking uploads (§4).
- **Lambda Validator:** <50 MB, reads SQS batch, validates object existence + checksum + MIME, deterministic `asset_id` (key+version hash), DynamoDB conditional write for idempotency (§22), quarantines invalid (§23), `StartExecution` for valid.

### 4.2 Validation & Idempotency (§22)
```
Incoming ASSET_CREATED
  → derive deterministic asset_id (s3 key+version)
  → DynamoDB ConditionExpression attribute_not_exists(PK=ASSET#<id>)
     ├─ exists → reconcile (check workflow_execution_id status) → ignore duplicate
     └─ new    → Put ASSET item (INGESTED) + JOB items (PENDING) → start Step Functions
Job key: asset_id + operation + pipeline_version → deterministic output URI
  → output exists? skip/reconcile : execute
```
Partial success preserved; successful jobs not repeated (§22 bullet 4).

### 4.3 Processing Plans (§10, §13)
Registry `asset_type → operations[]`:
- `video: [metadata, transcode_1080p, transcode_720p, thumbnail]`
- `image: [metadata, resize, thumbnail, format_conversion]`
- `audio: [metadata, normalize, format_conversion]`
- `document: [integrity, metadata_pages]` (extensible)
New operations require no ingestion contract change.

### 4.4 Orchestration — Step Functions (§14)
ASL `workflows/processing/definition.asl.json`:

- **Choice** by `asset_type` → select plan
- **Parallel** for independent jobs (e.g., metadata||1080p||thumbnail); dependencies modeled where needed (e.g., metadata before finalize)
- **Per-state:** `Retry` (bounded exponential: 3 attempts, Interval 2s, Backoff 2.0, Max 30s), `TimeoutSeconds`, `Catch` → `TerminalFailure`
- **ECS integration:** `arn:aws:states:::ecs:runTask.sync` + `WaitForTaskToken` where needed, Fargate task definitions per operation
- **Finalize state:** Lambda `finalizer` — verifies all required `operations[]` have `SUCCEEDED` + outputs exist + DQ checks (§24) → `PUBLISHED` else `FAILED` (never partial publish)

### 4.5 Compute — ECS Fargate (§15)
- **Contract (versioned):**
  Input: `{asset_id, operation, input_uri, output_uri, pipeline_version}`
  Output: `{asset_id, operation, status: SUCCEEDED|FAILED, output_uri, duration_ms, error_code?, checksum?}`
- Workers use task-role credentials (§26), structured JSON logs, safe to retry (idempotent S3 puts), no workflow state ownership.
- Sizing (benchmark-driven, §44): `metadata/thumbnail: 512 CPU/1024 MB`, `transcode: 1024 CPU/2048 MB`; VPC: Fargate in private subnets, NAT vs VPC endpoints decision logged (dev may use endpoints to avoid NAT cost in ap-south-1).
- Images: `Dockerfiles/{metadata,transcode,thumbnail,audio,document}.Dockerfile` — immutable versioned tags.

### 4.6 Operational State — DynamoDB (§21)
- **Table `frameops-assets-dev`:** `PK=ASSET#<asset_id>`, `SK=ASSET#<asset_id>` for asset item; `SK=JOB#<job_id>` for jobs. Attributes: `asset_type, status, source_uri, checksum, workflow_execution_id, created_at, updated_at` (asset); `operation, status, attempt, started_at, completed_at, error, retry_count` (job).
- **GSIs:** `GSI1 PK=status` for active work queries; `GSI2 PK=asset_type` for per-type counts. Final index design validated against access patterns: asset lookup, job history, active work, idempotency.
- Encryption at rest (KMS where justified), TTL for transient state if needed, PITR enabled in prod.

### 4.7 Data Platform — S3 Parquet + Glue + Athena (§19-20)
- **Datasets:** `asset_metadata` (canonical), `technical_metadata` (per-type fields Table 5), `processing_jobs` (history), `asset_lineage` (parent→derivative, pipeline_version)
- **Format:** Parquet Snappy, `year/month/day` partition (§20), schema enforced via Pydantic + DQ (§24)
- **Glue:** Crawler/catalog per dataset, `frameops_data_dev` database
- **Athena:** Workgroup `frameops-dev`, queries for §29 (ingested/day by type, success/failure by operation, p50/p95 durations, format distribution, storage growth, retries, DQ failure rate, derivatives/asset)

### 4.8 Reliability & Failure Handling (§23 Table 7, §37)
- **Transient** (timeout, API, interruption) → bounded exponential retry (Step Functions + SQS redelivery)
- **Permanent** (corrupt/unsupported) → no retry, quarantine `s3://.../quarantine/`, `TERMINAL_FAILURE`
- **Delivery/control** (repeated SQS consumer failure) → DLQ after 5 receives
- **Verification** (missing output/metadata) → do not publish, mark unresolved
- **Unknown** → terminal/frozen, alert, preserve evidence
- All external calls bounded with timeouts; no infinite retries; raw recoverable under retention (§37).

### 4.9 Data Quality (§24)
Pre-Parquet validation: required `asset_id` non-null/unique at grain, `asset_type` enum, valid timestamps, `file_size_bytes>0`, `status` controlled (`INGESTED..PUBLISHED|FAILED`), derivatives reference existing parent. Metrics: completeness, duplicate, orphan rates. Invalid → error/quarantine path, not Parquet.

### 4.10 Observability (§25)
- **Signals:** Platform (SQS depth/DLQ, ECS/SFN/Lambda failures), Asset (ingested/validated/published/failed by type), Job (duration, success/failure, retries by operation), DQ (invalid/duplicate/orphan), Infra (CPU/mem/latency/alarm state)
- **Alarms:** sustained backlog, DLQ growth, SFN failure spike, ECS failures, Lambda errors/throttles, DQ spikes — no paging per-asset.
- **Dashboard:** CloudWatch dashboard `FrameOps-dev` with widgets: Assets Today, Success %, Avg Duration, Queue Depth, DLQ, Active Jobs, Top Failure.

### 4.11 Security & Network (§26-27)
- Least-privilege IAM roles per §26 Table 9; short-lived task credentials; no secrets in logs/datasets/code/TF; bucket policies deny public; separate dev/prod roles/resources; no `AdministratorAccess`.
- TLS everywhere; S3/DynamoDB encryption at rest; KMS customer-managed where justified; lifecycle policies per retention (§44 configurable).
- VPC: managed services (S3, DynamoDB, SQS) outside VPC via endpoints; Fargate in VPC private subnets — NAT vs endpoints chosen on connectivity/cost (§44).

---

## 5. Data Contracts & Schemas

All versioned (`event_version`, `pipeline_version`), breaking changes require new version (§16.1).

- **ASSET_CREATED v1.0** (§16.1): `event_type, event_version, asset_id, asset_type, bucket, object_key, object_version, checksum, created_at`
- **UniversalAssetMetadata** (§17): `asset_id, asset_type, source, original_uri, status, file_name, mime_type, file_size_bytes, checksum, created_at, processed_at, processing_duration_ms`
- **TechnicalMetadata** (per-type Table 5): video `duration,width,height,fps,codec,bitrate,audio_tracks`; image `width,height,color_space,format,orientation`; audio `duration,codec,sample_rate,channels,bitrate`; document `page_count,file_format,author,creation_date,size`
- **ProcessingPlan** (§13): `{asset_id, asset_type, operations: [metadata, transcode_1080p, ...]}`
- **Job** (§12 Table 4): `job_id, asset_id, job_type, status: PENDING|RUNNING|SUCCEEDED|FAILED|RETRY|TERMINAL_FAILURE, attempt, duration_ms, retry_count`
- **Worker I/O** (§15): input `asset_id, operation, input_uri, output_uri`; output `asset_id, operation, status, output_uri, duration_ms`
- **Lineage** (§18): `parent_asset_id, child_asset_id, derivative_type, pipeline_version, created_at`; every derivative references parent+job

Schemas live in `data/schemas/*.py` (Pydantic v2), fixtures in `data/fixtures/` and `tests/fixtures/`, contract tests guard compatibility.

---

## 6. S3 & Partitioning (§19-20)

```
s3://frameops-assets-dev/
  raw/{video,image,audio,document}/<asset_id>/source.*
  processed/{video,image,audio,document}/<asset_id>/{1080p.mp4,720p.mp4,thumbnail.jpg,metadata.json}
  quarantine/<asset_id>/

s3://frameops-data-dev/
  asset_metadata/year=2026/month=08/day=25/part-*.parquet
  technical_metadata/...
  processing_jobs/...
  asset_lineage/...
```

Originals immutable; processed separate from raw; quarantine preserves evidence; Parquet Snappy; initial partition `year/month/day` (validate before high-cardinality partitions per §20).

---

## 7. Testing Strategy (§35 Table 10)

| Layer | Coverage | Tooling |
|-------|----------|---------|
| Unit | schemas, validation, plan selection, state transitions, idempotency, metadata parsing | pytest |
| Contract | event + worker I/O schemas, versioning | pytest + pydantic |
| Integration | S3/SQS/DynamoDB/SFN/ECS interactions | moto, local SFN simulator |
| Workflow | parallelism, retries, timeouts, partial failures, finalize gate | local SFN runner + fixtures |
| Data quality | schema/nulls/types/duplicates/orphan lineage/invalid values | great-expectations style checks |
| Security | IAM, bucket access, secret leakage/redaction | tfsec, checkov, grep tests |
| E2E | upload→PUBLISHED→Parquet→Athena (DuckDB locally) | fixtures + tmpdirs |
| Failure injection | transient, worker failure, corrupt, duplicate, DLQ | pytest parametrization |

Core logic testable locally before AWS (§34): `Fixture asset → Local event → Validator → Plan → Workflow sim → Processor → Output+metadata`.

---

## 8. Terraform Architecture (§32)

```
infrastructure/terraform/
  modules/{s3,eventbridge,sqs,lambda,step-functions,ecs,dynamodb,glue,athena,iam,vpc,monitoring}
  environments/dev/ap-south-1/{main.tf,variables.tf,outputs.tf,terraform.tfvars}
  environments/prod/  (isolated state, no sharing)
```

- Remote state: `s3://frameops-tfstate-dev-ap-south-1` + DynamoDB lock `frameops-tflock-dev`
- Dev/prod separate state files (§32); `fmt/validate/tfsec/plan` in CI; prod apply requires manual approval (§36).

---

## 9. Repository Structure (§33)

```
FrameOps/
  services/{validator,processor,metadata,finalizer}/
  workflows/processing/definition.asl.json
  data/{schemas,fixtures}/
  infrastructure/terraform/...
  tests/{unit,integration,fixtures}/
  Dockerfiles/
  docs/superpowers/specs/
  pyproject.toml
  README.md
```

Logical responsibilities (§33) remain clear even if container boundaries consolidate.

---

## 10. Roadmap — 16 Phases (§41)

| Phase | Deliverable | Exit Criteria |
|-------|-------------|---------------|
| 0 Bootstrap | Repo, Python project, lint/type, local harness | `make test` green on fixtures |
| 1 Contracts | Schemas + state machines | Contract tests pass, versioned |
| 2 Domain Core | Validation, plan registry, idempotency helpers | Unit tests, no AWS SDK in core |
| 3 Local Processors | ffmpeg/Pillow/pypdf workers, versioned containers | Local fixtures produce outputs+metadata |
| 4 Workflow | SFN ASL + local simulator, finalizer gate | Workflow tests: parallel/retries/timeouts |
| 5 Ingestion | S3/EventBridge/SQS/DLQ/Lambda TF + moto tests | Duplicate → single workflow |
| 6 Compute | ECS Fargate, IAM, VPC, task defs | Worker contract tests, retry-safe |
| 7 State | DynamoDB table, GSIs, conditional writes | Reconstruct asset/job state |
| 8 Data Platform | Parquet writers, Glue, Athena (DuckDB local) | Athena queries answer §29 |
| 9 Reliability | Retries, DLQ, quarantine, injection tests | All §23 cases demonstrated |
| 10 Observability | CloudWatch metrics/logs/alarms/dashboard | Alarms fire on injected backlog/DLQ |
| 11 Security | IAM/KMS/VPC/encryption/secret redaction review | Least-privilege audit pass |
| 12 Terraform | Modules, dev/prod state, remote backend | `tf apply` reproduces env (when approved) |
| 13 CI/CD | GitHub Actions: test→docker→tf plan→approve→deploy | Traceable to commit |
| 14 Optimization | Benchmark sizing/concurrency/cost/scans | Sizing & cost report |
| 15 Portfolio | Diagram, runbook, demos, README (§47) | End-to-end per asset type |

MVP (§40) is complete when phases 0-8 + reliability/observability signals are green locally; AWS deploy is Phase 5-12 upon approval.

---

## 11. Acceptance & Done (§42-43)

Acceptance (§42): multi-format S3, duplicate safety, differing plans, parallel jobs, SFN retries/timeouts/terminal, retry-safe workers, DynamoDB reconstructable, raw immutable, quarantine, DLQ, PUBLISHED gate, Parquet+Athena+Glue, CloudWatch signals, least-privilege IAM, TF reproducibility, local testability, E2E trace.

Done (§43): deployed arch matches spec (or deviations documented), versioned schemas, E2E per asset type, duplicate/retry/DLQ/quarantine/partial-failure demos, operational/analytical separation, Athena analysis, dashboard/alarms, IAM review, TF reproducibility, docs + known limitations.

---

## 12. Open Decisions (§44) & Resolutions

| Decision | Direction (locked) | When finalized |
|----------|-------------------|----------------|
| Fargate sizing | `512/1024` metadata, `1024/2048` transcode; benchmark after Phase 3 | Post-rep workload tests |
| VPC connectivity | Dev: VPC endpoints to avoid NAT cost in ap-south-1; prod: evaluate NAT | Before prod hardening |
| DynamoDB indexes | GSI `status` + `asset_type` baseline; refine after access-pattern tests | After Phase 7 |
| Parquet partitioning | `year/month/day` baseline; high-cardinality only after Athena tests | After Phase 8 |
| Retention | Configurable lifecycle vars | Before prod |
| API/control plane | Deferred (§28) | Only if consumer |
| Processors | Operation registry extensible | As formats expand |
| AI enrichment | Future | After core stable |

---

## 13. Future Extensions (§45)

Additional formats, registry operations, GPU if economics justify, MediaConvert where managed transcoding preferred, moderation/semantic enrichment, search index, downstream distribution events, QuickSight, cross-account/multi-tenant, multi-region — none are MVP; each requires workload justification (§50 bullet 7).

---

## 14. Source-of-Truth Rules (§50)

1. This doc + Master Spec are authoritative; deviations documented.
2. Multi-format S3 boundary intact.
3. Step Functions remains orchestration boundary.
4. Fargate is baseline heavy compute unless measured justification.
5. Operational vs analytical separation.
6. Idempotency, failure handling, DQ, observability mandatory.
7. No service added for resume value.

---

## Appendix: Analytical Questions (§29) — Athena Targets

- Assets ingested/day by type
- Success/failure rate by operation
- Avg/p50/p95 durations
- Format/codec/resolution distribution
- Storage growth rate
- Jobs with most retries
- DQ failure %
- Derivatives per asset
- Throughput under burst (100/hr normal vs 20k/10m burst per §30)

These justify the S3/Parquet/Glue/Athena layer.

