# FrameOps — Event-Driven Media Asset Processing & Data Platform

> **Source of Truth:** `FrameOps_Master_Project_Specification_v1.docx` + `docs/superpowers/specs/2026-08-27-frameops-design.md`
> **Implementation Plan:** `docs/superpowers/plans/2026-08-27-frameops-implementation.md`
> **Region:** `ap-south-1` (local-first MVP)

## Architecture

```
S3 (raw/processed/quarantine + s3://frameops-data/*)
  → EventBridge → SQS → DLQ
  → Lambda Validator (dedup + DynamoDB + Step Functions start)
  → Step Functions (plan selection, Parallel, retries/timeouts, finalizer)
  → ECS Fargate workers (ffmpeg/Pillow/pypdf)
  → S3 Processed + DynamoDB State → Finalizer gate (PUBLISHED/FAILED)
  → S3 Data Lake Parquet → Glue → Athena
  • IAM/KMS/VPC/CloudWatch/Terraform cross-cutting
```

See design doc for full component breakdown (§4).

## Quick Start (Local)

```bash
pip install -e ".[dev]"
make test        # pytest
make lint        # ruff
make type        # mypy
make all
```

No AWS credentials required for local tests — all AWS SDK calls are mocked via `moto`, Athena via `DuckDB`.

## Repository Structure

```
services/{validator,processor,metadata,finalizer}  # domain logic
workflows/processing/definition.asl.json           # Step Functions ASL
data/schemas/                                      # Pydantic contracts
infrastructure/terraform/                          # IaC (drafted, not applied)
tests/{unit,integration,fixtures}/
Dockerfiles/
docs/superpowers/{specs,plans}/
```

## Roadmap

16 phases per Master Spec §41. MVP phases 0-8 + reliability/observability green locally before any `terraform apply`.
Deviations from spec are documented per §50.

## Portfolio Narrative

**Problem:** Heterogeneous media arrives continuously and needs different, reliable workflows.
**Naive:** Synchronous app-centric processing.
**Why it fails:** Bursty, long-running, heterogeneous, failure-prone.
**FrameOps:** S3→EventBridge→SQS→Lambda→Step Functions→ECS | Data: S3/Parquet→Glue→Athena | Reliability: retries+DLQ+quarantine+idempotency+DynamoDB.

## License

Private — portfolio reference implementation.
