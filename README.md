# FrameOps — Event-Driven Media Asset Processing & Data Platform

> **Source of Truth:** `FrameOps_Master_Project_Specification_v1.docx` + `docs/superpowers/specs/2026-08-27-frameops-design.md`
> **Plan:** `docs/superpowers/plans/2026-08-27-frameops-implementation.md` · **Region:** `ap-south-1` · **Mode:** Local-first MVP

## Problem (Spec §4)

Large volumes of heterogeneous assets (video, image, audio, PDF) arrive continuously and need different, reliable workflows. Naive synchronous app-centric processing fails: bursty, long-running, heterogeneous, failure-prone. Operators need lineage, state, DLQ, and analytical datasets.

**FrameOps turns every asset into a governed, traceable, reusable data object:**

`Ingest → Validate → Plan → Orchestrate (Parallel) → Fargate → Finalize → Publish → Data Lake → Athena`

## Architecture (Spec §7)

```
Media Sources
  → S3 (raw/processed/quarantine + s3://frameops-data/*) — ObjectCreated
  → EventBridge → SQS → DLQ (5 receives)
  → Lambda Validator (lightweight, dedup via DynamoDB conditional writes, Step Functions start)
  → Step Functions (branch by asset_type, Parallel jobs, ECS RunTask sync, bounded retries/timeouts, Finalize gate)
  → ECS Fargate workers (ffmpeg/Pillow/pypdf, versioned, retry-safe, task-role creds)
  → S3 Processed + DynamoDB (ASSET#id, JOB#id, GSIs) → Finalizer (PUBLISHED only if all required ops SUCCEEDED + outputs exist + DQ)
  → S3 Data Lake Parquet (Snappy, year/month/day) → Glue → Athena
  • IAM (least privilege) · KMS · VPC (Fargate private + S3/DynamoDB endpoints) · CloudWatch (logs/metrics/alarms/dashboard) · Terraform (dev/prod isolated state) · CI/CD
```

Responsibility boundaries per Spec §8 Table 2 — S3 storage, EventBridge routing, SQS reliability, Lambda control, Step Functions workflow, Fargate compute, DynamoDB state.

## Quick Start (Local — no AWS creds)

```bash
pip install -e ".[dev]"
make test        # 32+ tests: unit + contract + integration + workflow + e2e + reliability + observability + security
make lint        # ruff
make type        # mypy strict
make all         # lint + type + test
pytest tests/integration/test_e2e.py -v  # upload→PUBLISHED→Parquet→Athena (DuckDB)
```

Local harness: `moto` for S3/SQS/DynamoDB, `DuckDB` for Athena, `Pillow` for image, `pypdf` for PDF, `pyarrow` Parquet. Heavy ffmpeg runs in Fargate (Dockerfiles/).

## Repository Structure (Spec §33)

```
services/{validator,processor,metadata,finalizer,reliability,observability,security}
workflows/processing/definition.asl.json  # Step Functions ASL (ap-south-1)
data/schemas/  # Pydantic v2 contracts (versioned, breaking → new version §16.1)
infrastructure/terraform/modules/{s3,eventbridge,sqs,lambda,step-functions,ecs,dynamodb,glue,athena,iam,vpc,monitoring,kms}
infrastructure/terraform/environments/{dev,prod}/ap-south-1
tests/{unit,integration,fixtures}
Dockerfiles/{metadata,transcode,thumbnail}.Dockerfile
docs/{superpowers/{specs,plans},runbook.md,demo.md}
```

## Demo Scenarios (Spec §38-39)

```bash
# Video: metadata + 1080p + thumbnail in parallel → Fargate → PUBLISHED
pytest tests/integration/test_workflow.py::test_parallel_metadata_and_thumbnail -v

# Image/Audio/Document: type-specific plans differ
python -c "from services.processor.plan import get_plan; print(get_plan('video')); print(get_plan('image'))"

# Duplicate → idempotent: one workflow
pytest tests/integration/test_ingestion.py::test_duplicate_event_idempotent -v

# Corrupt → quarantine + TERMINAL_FAILURE (no blind retry)
pytest tests/integration/test_reliability.py::test_corrupt_asset_quarantined -v

# SQS → DLQ after 5 receives
pytest tests/integration/test_reliability.py::test_dlq_after_5_failures -v

# E2E → Parquet → Athena
pytest tests/integration/test_e2e.py -v
```

See `docs/demo.md` and `docs/runbook.md`.

## Analytical Queries (Spec §29)

Ingested/day by type, success/failure by operation, p50/p95 durations, format distribution, storage growth, retries, DQ failure %, derivatives/asset, throughput under burst (100/hr normal vs 20k/10m §30). Implemented via `services/metadata/parquet_writer.py` + Glue + Athena (DuckDB locally).

## Reliability (Spec §23, §37)

At-least-once assumed. Transient → bounded exponential retry (3, 2s×2.0 capped 30s). Permanent → quarantine `s3://.../quarantine/` + `TERMINAL_FAILURE`. SQS redelivery → DLQ. Verification gate — missing output → not PUBLISHED. Raw recoverable.

## Security & Costing (Spec §26-31)

Least-privilege IAM per Table 9, KMS, TLS, bucket policies deny public, VPC endpoints (dev avoids NAT cost §44), dev/prod isolated, no secrets in logs/code/TF. Fargate is primary variable cost; Parquet partitioning reduces Athena scans.

## Terraform

```bash
cd infrastructure/terraform/environments/dev/ap-south-1
terraform init   # backend s3://frameops-tfstate-dev-ap-south-1
terraform plan
# prod requires manual approval per Spec §36
```

Modules drafted — not applied until explicit approval (local-first).

## Roadmap (Spec §41)

0 Bootstrap → 1 Contracts → 2 Domain → 3 Processors → 4 Workflow → 5 Ingestion → 6 Compute → 7 State → 8 Data → 9 Reliability ✓ → 10 Observability ✓ → 11 Security ✓ → 12 Terraform/CI ✓ → 13 Optimization → 14 Portfolio

## Definition of Done (Spec §43)

Versioned schemas, E2E per asset type, duplicate/retry/DLQ/quarantine/partial-failure demos, operational/analytical separation, Athena analysis, dashboard/alarms, IAM review, TF reproducibility, docs + known limitations.

## License

Private — portfolio reference implementation.
