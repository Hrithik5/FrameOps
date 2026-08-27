# FrameOps — Event-Driven Media Asset Processing & Data Platform

> **Version:** `v0.2.0` — `2026-08-27` · **Build:** `7c5c5da` (42 tests, ruff/mypy clean) · **Region:** `ap-south-1` · **Mode:** Local-first MVP · **Lake:** Flat (no layered stages, <1M optimized)
> **Source of Truth:** `FrameOps_Master_Project_Specification_v1.docx` (50 sections, Verification PASS)
> **Design:** `docs/superpowers/specs/2026-08-27-frameops-design.md` · **Plan:** `docs/superpowers/plans/2026-08-27-frameops-implementation.md` · **Decisions:** `docs/design-decisions.md`

## Current Status (up to now)

| Area | State | Evidence |
|------|-------|----------|
| **Phases 0-8** Bootstrap → Contracts → Domain → Processors → Workflow → Ingestion → Compute → State → Data Platform | ✅ Complete | `pyproject.toml:1`, `data/schemas/*`, `services/validator/*`, `workflows/processing/definition.asl.json:1` |
| **Phase 9 Reliability** Retries, DLQ, quarantine, injection | ✅ Complete | `services/reliability/*`, `tests/integration/test_reliability.py:1` (6 tests) |
| **Phase 10 Observability** CloudWatch metrics/alarms/dashboard | ✅ Complete | `services/observability/*`, `infrastructure/terraform/modules/monitoring/*`, `tests/unit/test_observability.py:1` |
| **Phase 11 Security** IAM least-privilege, KMS, VPC, redact | ✅ Complete | `services/security/*`, `modules/iam,kms,vpc`, `tests/unit/test_security.py:1` |
| **Phase 12 Terraform + CI** dev/prod isolated state, CI/CD | ✅ Draft | `infrastructure/terraform/environments/dev/ap-south-1/main.tf:1`, `.github/workflows/ci.yml:1` — `terraform plan` not yet applied (local-first per Q1=A) |
| **Phase 13 Portfolio** README, runbook, demo | ✅ Complete | `docs/runbook.md:1`, `docs/demo.md:1` |
| **Tests** | ✅ 42 passed | `pytest -q → 42 passed in 0.43s` (18 unit + 14 integration incl. e2e) |
| **Static** | ✅ Clean | `mypy services data → Success`, `ruff check → All checks passed` |
| **Data Volume** | <1M | Flat lake, simple Athena search — no layered duplication (see `docs/design-decisions.md:122`) |

**Commits:** `a72242f` design → `a72eb32` plan → `6b4d3e3` bootstrap/contracts/processors/workflow/data → `0de6809` reliability/observability/security/CI → `7c5c5da` design decisions → current (flat lock + README update).

## Problem (Spec §4)

Large volumes of heterogeneous assets (video, image, audio, PDF) arrive continuously and need different, reliable workflows. Naive synchronous app-centric processing fails: bursty, long-running, heterogeneous, failure-prone. Operators need lineage, state, DLQ, and analytical datasets.

**FrameOps turns every asset into a governed, traceable, reusable data object:**

`Ingest → Validate → Plan → Orchestrate (Parallel) → Fargate → Finalize → Publish → Data Lake → Athena`

## Final Architecture (Locked 2026-08-27)

```
Media Sources (Video | Image | Audio | PDF)
  → S3 (raw/processed/quarantine + s3://frameops-data/*) — ObjectCreated
  → EventBridge (event routing) → SQS (buffer + retry, visibility 300s) → DLQ (maxReceive 5)
  → Lambda Validator (lightweight, dedup via DynamoDB conditional writes, Step Functions start) — <50MB
  → Step Functions (Choice by asset_type, Parallel branches, ECS RunTask sync, bounded retries 3×2s×2.0 capped 30s, Timeout 300/1800, Finalize gate)
  → ECS Fargate workers (ffmpeg/Pillow/pypdf, versioned, retry-safe, task-role creds) — 512/1024 metadata, 1024/2048 transcode
  → S3 Derivatives + DynamoDB (ASSET#id, JOB#id, GSIs status/asset_type) → Finalizer (PUBLISHED only if all required ops SUCCEEDED + outputs exist + DQ)
  → S3 Data Lake Parquet (Snappy, year/month/day, 4 datasets: asset_metadata, technical_metadata, processing_jobs, asset_lineage) → Glue Data Catalog (frameops_data_dev) → Athena (workgroup frameops-dev)
  • IAM least-privilege (Table 9) · KMS (rotation) · VPC (private subnets + S3/DynamoDB endpoints, dev avoids NAT) · CloudWatch (logs/metrics/6 alarms/dashboard) · Terraform (dev/prod isolated state) · CI/CD (test→lint→type→docker→tf fmt/validate/plan→approval)
```

Responsibility boundaries per Spec §8 Table 2 — S3 storage, EventBridge routing, SQS reliability, Lambda control, Step Functions workflow, Fargate compute, DynamoDB state.

## Quick Start (Local — no AWS creds)

```bash
pip install -e ".[dev]"
make test        # 42 tests: unit + contract + integration + workflow + e2e + reliability + observability + security
make lint        # ruff
make type        # mypy strict (37 files)
make all         # lint + type + test
pytest tests/integration/test_e2e.py -v  # upload→PUBLISHED→Parquet→Athena (DuckDB)
pytest -v                                 # per-module isolation, then combined 42
```

Local harness: `moto` for S3/SQS/DynamoDB, `DuckDB` for Athena, `Pillow` for image, `pypdf` for PDF, `pyarrow` Parquet Snappy. Heavy ffmpeg runs in Fargate (`Dockerfiles/metadata.Dockerfile:1`, `transcode`, `thumbnail`).

## Repository Structure (Spec §33)

```
services/{validator,processor,metadata,finalizer,reliability,observability,security}
workflows/processing/definition.asl.json  # Step Functions ASL (ap-south-1)
data/schemas/  # Pydantic v2 contracts (versioned, breaking → new version §16.1)
infrastructure/terraform/modules/{s3,eventbridge,sqs,lambda,step-functions,ecs,dynamodb,glue,athena,iam,vpc,monitoring,kms}
infrastructure/terraform/environments/{dev,prod}/ap-south-1  # isolated state s3://frameops-tfstate-{dev,prod}-ap-south-1 + frameops-tflock-*
tests/{unit,integration}  # 42 tests
Dockerfiles/{metadata,transcode,thumbnail}.Dockerfile  # python:3.11-slim + ffmpeg
docs/{superpowers/{specs,plans},design-decisions.md,runbook.md,demo.md}
```

## Demo Scenarios (Spec §38-39)

```bash
# Video: metadata + 1080p + thumbnail in parallel → Fargate → PUBLISHED
pytest tests/integration/test_workflow.py::test_parallel_metadata_and_thumbnail -v

# Image/Audio/Document: type-specific plans differ
python -c "from services.processor.plan import get_plan; print(get_plan('video')); print(get_plan('image'))"

# Duplicate → idempotent: one workflow (deterministic asset_id + conditional DynamoDB)
pytest tests/integration/test_ingestion.py::test_duplicate_event_idempotent -v

# Corrupt → quarantine + TERMINAL_FAILURE (no blind retry)
pytest tests/integration/test_reliability.py::test_corrupt_asset_quarantined -v

# SQS → DLQ after 5 receives
pytest tests/integration/test_reliability.py::test_dlq_after_5_failures -v

# E2E → Parquet → Athena (DuckDB local)
pytest tests/integration/test_e2e.py -v
```

See `docs/demo.md:1` and `docs/runbook.md:1`.

## Analytical Queries (Spec §29)

Ingested/day by type, success/failure by operation, p50/p95 durations, format distribution, storage growth, retries, DQ failure %, derivatives/asset, throughput under burst (100/hr normal vs 20k/10m §30). Implemented via `services/metadata/parquet_writer.py:27` (validated, Snappy) + Glue + Athena (DuckDB locally). Flat `asset_metadata` denormalizes technical fields for `SELECT * FROM asset_metadata WHERE mime_type='video/mp4' AND year=2026` pruning.

## Reliability (Spec §23, §37)

At-least-once assumed. Transient (`Timeout, Throttling`) → bounded exponential `3 × 2s ×2.0 capped 30s` (`services/reliability/retry.py:28`). Permanent (`Corrupt`) → quarantine `s3://.../quarantine/<id>/` (`services/reliability/quarantine.py:5`) + `TERMINAL_FAILURE`. SQS redelivery ×5 → DLQ (`services/reliability/dlq.py:12`). Verification gate — missing output → `FAILED` (`services/finalizer/handler.py:14`). Raw recoverable. Tested `tests/integration/test_reliability.py:1` (6 cases).

## Security & Costing (Spec §26-31)

Least-privilege IAM per Table 9 (`services/security/iam.py:5`, `modules/iam:5 resources`), KMS rotation (`modules/kms`), TLS, bucket policies deny public + insecure transport, VPC endpoints (dev avoids NAT cost §44), dev/prod isolated, no secrets in logs/code/TF (`services/security/redact.py:1` AWS key pattern) — verified `tests/unit/test_security.py:1`. Fargate primary variable cost; Parquet `year/month/day` reduces Athena scans.

## Terraform

```bash
cd infrastructure/terraform/environments/dev/ap-south-1
terraform init   # backend s3://frameops-tfstate-dev-ap-south-1 + frameops-tflock-dev (isolated, §32 no shared state)
terraform plan   # fmt/validate/tfsec in CI
terraform apply  # dev only; prod requires manual approval per .github/workflows/ci.yml:1 and Spec §36
```

Modules: `iam,kms,vpc,monitoring` real (5,2,5,5 resources); `s3,sqs,eventbridge,lambda,step-functions,ecs,dynamodb,glue,athena` drafted `TODO` 26 lines — local-first, completes on your nod (42 tests already green). See `infrastructure/terraform/README.md:1`.

## Roadmap (Spec §41 — Current Progress)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 Bootstrap | Repo, Python 3.11+, lint/type, harness | ✅ |
| 1 Contracts | Schemas + state machines (versioned) | ✅ |
| 2 Domain Core | Validation, plan registry, idempotency | ✅ |
| 3 Local Processors | ffmpeg/Pillow/pypdf workers, versioned containers | ✅ |
| 4 Workflow | SFN ASL + local simulator, finalizer gate | ✅ |
| 5 Ingestion | S3/EventBridge/SQS/DLQ/Lambda TF + moto tests | ✅ (TF draft) |
| 6 Compute | ECS Fargate, IAM, VPC | ✅ (TF draft) |
| 7 State | DynamoDB table, GSIs, conditional writes | ✅ (TF draft) |
| 8 Data Platform | Parquet writers, Glue, Athena (DuckDB local) | ✅ (TF draft) |
| 9 Reliability | Retries, DLQ, quarantine, injection | ✅ |
| 10 Observability | CloudWatch metrics/logs/alarms/dashboard | ✅ |
| 11 Security | IAM/KMS/VPC/encryption/redaction | ✅ |
| 12 Terraform | Modules, dev/prod state, remote backend | ✅ Draft |
| 13 CI/CD | GitHub Actions test→docker→tf plan→approval | ✅ |
| 14 Optimization | Benchmark sizing/concurrency/cost/scans | ⬜ Next |
| 15 Portfolio | Diagram, runbook, demos, README, decisions | ✅ |

## Definition of Done (Spec §43 — Current)

Versioned schemas, E2E per asset type, duplicate/retry/DLQ/quarantine/partial-failure demos, operational/analytical separation, Athena analysis, dashboard/alarms, IAM review, TF reproducibility (draft), docs + known limitations — `pytest -q 42 passed`, `mypy`/`ruff` clean, `docs/design-decisions.md:1` records every locked choice (14 sections).

## Changelog

* `2026-08-27 v0.2.0` — Locked flat lake (no layered stages per <1M), removed all layered labels, 42 tests, 14 decision sections, 12 TF modules, 3 Dockerfiles, CI/CD, runbook/demo. Build `7c5c5da`.
* `2026-08-27 v0.1.0` — Bootstrap, contracts, processors, workflow, data platform.

## License

Private — portfolio reference implementation.
