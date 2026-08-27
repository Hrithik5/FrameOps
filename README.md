# FrameOps — Event-Driven Media Asset Processing & Data Platform

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.2.0%20frozen-blue" alt="version">
  <img src="https://img.shields.io/badge/tests-42%20passed-brightgreen" alt="tests">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB" alt="python">
  <img src="https://img.shields.io/badge/terraform-%3E%3D1.5-623CE4" alt="terraform">
  <img src="https://img.shields.io/badge/license-private-lightgrey" alt="license">
  <br/>
  <sub>Source of Truth: <code>FrameOps_Master_Project_Specification_v1.docx</code> (50 sections) • <a href="docs/superpowers/specs/2026-08-27-frameops-design.md">Design</a> • <a href="docs/superpowers/plans/2026-08-27-frameops-implementation.md">Plan</a> • <a href="docs/design-decisions.md">Decisions</a></sub>
</p>

> **One-line pitch:** FrameOps turns every video, image, audio, and PDF into a governed, traceable, reusable data object — ingested once, processed in parallel, queried via Athena.

**Live repo:** `https://github.com/Hrithik5/FrameOps.git` · **Region:** `YOUR_AWS_REGION` (placeholder, was `ap-south-1`) · **Mode:** Local-first MVP, flat lake (<1M, no layered duplication) · **State:** Frozen `06c3603` + `a3fac2d` (credential-proof)

---

## Table of Contents

- [Problem](#problem)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Quick Start (Local)](#quick-start-local)
- [Testing](#testing)
- [Deployment (AWS)](#deployment-aws)
- [Demo Scenarios](#demo-scenarios)
- [Data Platform & Queries](#data-platform--queries)
- [Reliability, Observability, Security](#reliability-observability-security)
- [Cost](#cost)
- [Roadmap](#roadmap)
- [Changelog](#changelog)

---

## Problem

Heterogeneous assets arrive continuously and need different, reliable workflows. A naive synchronous service fails: bursty traffic, long-running transcodes, heterogeneous formats, and no lineage. FrameOps solves it with an **event-driven pipeline** where S3 is the universal boundary and every asset follows `Ingest → Validate → Plan → Orchestrate (Parallel) → Fargate → Finalize → Publish → Lake → Athena`.

## Architecture

```
Digital Assets (Video | Image | Audio | PDF)
        │
        ▼
Amazon S3 (raw/processed/quarantine + s3://frameops-data/*) — ObjectCreated
        │
        ▼
EventBridge (routing) → SQS (buffer, visibility 300s, DLQ maxReceive 5) → DLQ
        │
        ▼
Lambda Validator (lightweight, <50MB, dedup via DynamoDB conditional writes, Step Functions start)
        │
        ▼
Step Functions (Choice by asset_type, Parallel branches, ecs:runTask.sync, retries 3×2s×2.0 capped 30s, Finalize gate)
        │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Metadata      Transcode      Thumbnail  (Audio / Document branches)
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 ECS Fargate (512/1024 metadata/thumbnail, 1024/2048 transcode, ECR, task-role)
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
   S3 Derivatives              DynamoDB (PK=ASSET#id, SK=JOB#id, GSI status)
         │                           │
         └─────────────┬─────────────┘
                       ▼
              S3 Data Lake Parquet (Snappy, year/month/day)
              4 datasets: asset_metadata, technical_metadata, processing_jobs, asset_lineage
                       │
                       ▼
                Glue Catalog (frameops_dev) → Athena (workgroup frameops-dev)

Cross-cutting: IAM (least-privilege Table 9) · KMS (rotation) · VPC (private subnets + S3/Dynamo/ECR/Logs endpoints, no NAT) · CloudWatch (30d logs, 6 alarms, dashboard) · Terraform (dev/prod isolated state, S3 backend use_lockfile) · CI/CD
```

**Boundaries (§8):** S3 storage, EventBridge routing, SQS reliability, Lambda control, Step Functions workflow, Fargate compute, DynamoDB state. Originals immutable (`raw/` never overwritten).

## Features

- **Universal ingestion:** One S3 prefix per type (`raw/{video,image,audio,document}/<id>/source.*`), `ObjectCreated` → EventBridge → SQS.
- **Plan registry:** `video → [metadata,1080p,720p,thumbnail]`, `image → [metadata,resize,thumbnail]`, etc. (`services/processor/plan.py:6`), extensible without ingestion change.
- **Parallel orchestration:** `ParallelImage/Video/Audio/Document` branches with per-state `Retry`/`Catch` and `Timeout` (`workflows/processing/definition.asl.json:1`, `.tpl` for AWS).
- **Idempotent:** `deterministic_asset_id` (SHA256 `bucket/key#version`), `output_uri` deterministic, `ConditionExpression attribute_not_exists(PK)` (§22).
- **Failure taxonomy:** Transient → bounded exponential `3 × 2s ×2.0 capped 30s`, Permanent → `s3://.../quarantine/`, Delivery → DLQ, Verification → `FAILED` (not `PUBLISHED`).
- **Flat lake (<1M):** No layered duplication — 4 Parquet datasets, Snappy, `year/month/day`, Glue + Athena via `DuckDB` locally.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python `3.11` | Lambda/Fargate base, `pydantic v2`, `boto3` |
| Contracts | Pydantic v2 | Versioned `ASSET_CREATED v1.0` (§16.1) |
| Processors | `ffmpeg/ffprobe`, `Pillow`, `pypdf` | Fargate heavy, local stubs via `Pillow` |
| State | DynamoDB `PAY_PER_REQUEST` | `PK/SK` + `GSI1` status, PITR |
| Lake | `pyarrow` Parquet Snappy | Columnar, Athena-prunable |
| IaC | Terraform `>=1.5` | 12 modules, `dev`/`prod` isolated `s3://frameops-tfstate-*` |
| CI | GitHub Actions | `test → lint → type → docker → tf fmt/validate/plan → approval` |
| Containers | `python:3.11-slim` | `Dockerfiles/{metadata,transcode,thumbnail}.Dockerfile` |

## Repository Structure

```
FrameOps/
├── FrameOps_Master_Project_Specification_v1.docx  # 50 sections, verification PASS
├── pyproject.toml, Makefile, .gitignore           # ruff/mypy/pytest, >=3.11
├── services/
│   ├── validator/{core.py,handler.py}             # pure validation + SQS→ DynamoDB→SFN handler
│   ├── processor/{plan.py,idempotency.py,metadata.py,thumbnail.py,transcode.py,audio.py,document.py}
│   ├── metadata/{builder.py,parquet_writer.py}    # Parquet Snappy, DQ
│   ├── finalizer/handler.py                       # PUBLISHED gate
│   ├── reliability/{retry.py,quarantine.py,dlq.py} # bounded retry, DLQ 5
│   ├── observability/{metrics.py,alarm_config.py} # 6 alarms, dashboard
│   └── security/{iam.py,redact.py}                # least-privilege, redaction
├── data/schemas/{events.py,asset.py,technical.py,jobs.py,worker.py,lineage.py}
├── workflows/processing/
│   ├── definition.asl.json      # static dev (simulator)
│   ├── definition.asl.json.tpl  # templated for AWS (Cluster, NetworkConfiguration)
│   └── simulator.py             # ThreadPoolExecutor(4) local
├── infrastructure/terraform/
│   ├── modules/{s3,sqs,dynamodb,eventbridge,lambda,step-functions,ecs,glue,athena,iam,kms,vpc,monitoring}
│   └── environments/{dev,prod}/YOUR_AWS_REGION/  # backend s3 use_lockfile
├── tests/{unit,integration}     # 42 tests
├── Dockerfiles/{metadata,transcode,thumbnail}.Dockerfile
├── build/lambda_validator/      # real validator zip (handler + services + data, no pydantic layer)
└── docs/{design-decisions.md,runbook.md,demo.md,superpowers/{specs,plans}}
```

## Quick Start (Local — no AWS creds)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Lint / type / test
make lint   # ruff
make type   # mypy strict — 37 files
make test   # pytest -q → 42 passed (0.4s)
make all    # all three

# 3. Run a single layer
pytest tests/integration/test_e2e.py -v   # S3→PUBLISHED→Parquet→Athena via DuckDB
pytest tests/integration/test_workflow.py -v  # Parallel metadata+thumbnail
```

Local harness: `moto` for S3/SQS/DynamoDB, `DuckDB` for Athena, `Pillow` for image, `pypdf` for PDF.

## Testing

| Layer | Command | What it proves |
|-------|---------|----------------|
| Unit | `pytest tests/unit -v` | 18 tests: schemas, plan, validator, idempotency |
| Contract | `pytest tests/unit/test_events.py -v` | `ASSET_CREATED v1.0` breaking → new version |
| Integration | `pytest tests/integration/test_ingestion.py -v` | SQS duplicate → single DynamoDB `Put` |
| Workflow | `pytest tests/integration/test_workflow.py -v` | `ParallelImage` 2 branches, `Finalize` gate |
| Data | `pytest tests/integration/test_data_platform.py -v` | Snappy + DQ `file_size_bytes>0` |
| Reliability | `pytest tests/integration/test_reliability.py -v` | 6 cases: retry, backoff, DLQ 5, quarantine |
| Security | `pytest tests/unit/test_security.py -v` | no `AdministratorAccess`, redaction |
| E2E | `pytest tests/integration/test_e2e.py -v` | `raw/image` → `PUBLISHED` → `asset_metadata` → Athena |

**Combined:** `pytest -v` → `42 passed` (18 unit + 24 integration).

## Deployment (AWS)

> **Frozen:** `YOUR_AWS_ACCOUNT_ID`/`YOUR_AWS_REGION` are placeholders in `infrastructure/**/*.tf` and `workflows/definition.asl.json`. Replace with your `ap-south-1`/`559050238050` (or yours) before `plan`.

```bash
# 1. Backend bucket (once, S3 native lock, no DynamoDB table)
aws s3 mb s3://frameops-tfstate-dev-YOUR_AWS_REGION --region YOUR_AWS_REGION --profile YOUR_AWS_PROFILE
aws s3api put-bucket-versioning --bucket frameops-tfstate-dev-YOUR_AWS_REGION --versioning-configuration Status=Enabled

# 2. Init & plan (local state if backend commented, or S3 use_lockfile if enabled)
terraform -chdir=infrastructure/terraform/environments/dev/YOUR_AWS_REGION init -reconfigure
terraform -chdir=infrastructure/terraform/environments/dev/YOUR_AWS_REGION plan -out=/tmp/tfplan
# expect 60-68 to add (12 modules: s3, sqs+dlq, dynamodb, eventbridge, lambda 2, sfn, ecs 3 repos+5 tasks, glue 4 crawlers, athena, kms, vpc 2 subnets+SG+5 endpoints, monitoring)

# 3. Apply (needs your approval, < $1 for 10 assets test)
terraform -chdir=infrastructure/terraform/environments/dev/YOUR_AWS_REGION apply /tmp/tfplan

# 4. Push dummy images so Fargate can pull (otherwise CannotPullContainerError)
aws ecr get-login-password --region YOUR_AWS_REGION --profile YOUR_AWS_PROFILE | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.YOUR_AWS_REGION.amazonaws.com
for repo in metadata transcode thumbnail audio document; do
  docker pull public.ecr.aws/docker/library/busybox:latest
  docker tag busybox:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.YOUR_AWS_REGION.amazonaws.com/frameops-$repo:latest
  docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.YOUR_AWS_REGION.amazonaws.com/frameops-$repo:latest
done
```

**Destroy (no cost after):**
```bash
terraform -chdir=infrastructure/terraform/environments/dev/YOUR_AWS_REGION destroy -auto-approve
# S3/DynamoDB/SQS/Lambda/SFN/ECS/Glue/Athena/KMS/VPC all deleted; KMS pending deletion 7d ($3)
```

## Demo Scenarios

```bash
# Upload correct key (folders are the key — no need to create empty folders first)
aws s3 cp /tmp/source.jpg s3://frameops-assets-YOUR_ENV-YOUR_AWS_ACCOUNT_ID/raw/image/asset-001/source.jpg --region YOUR_AWS_REGION --profile YOUR_AWS_PROFILE

# Check each hop (console easier: search frameops-dev)
aws sqs get-queue-attributes --queue-url $(terraform output -raw queue_url) --attribute-names ApproximateNumberOfMessages
aws logs tail /aws/lambda/frameops-dev-validator --since 2m
aws stepfunctions list-executions --state-machine-arn $(terraform output -raw state_machine_arn) # Succeeded green
aws s3 ls s3://frameops-assets-.../processed/asset-001/ --recursive
aws dynamodb get-item --table-name frameops-dev-assets --key '{"PK":{"S":"ASSET#asset-001"},"SK":{"S":"ASSET#asset-001"}}'
```

See `docs/demo.md` and `docs/runbook.md` for console click paths (`S3` → `Step Functions` graph → `DynamoDB` → `Athena`).

## Data Platform & Queries

Flat lake: `s3://frameops-data-.../{asset_metadata,technical_metadata,processing_jobs,asset_lineage}/year=YYYY/month=MM/day=DD/part-*.parquet` (validated `file_size_bytes>0` in `parquet_writer.py:11`).

```sql
-- Athena workgroup frameops-dev (results s3://.../athena-results/, SSE_S3)
SELECT asset_id, asset_type, status FROM "frameops_dev"."asset_metadata" LIMIT 10;
SELECT asset_type, count(*) FROM "frameops_dev"."asset_metadata" GROUP BY asset_type;
SELECT operation, avg(duration_ms) FROM "frameops_dev"."processing_jobs" GROUP BY operation;
```

Local: `DuckDB` `read_parquet` mirrors Athena (`tests/integration/test_data_platform.py:38`).

## Reliability, Observability, Security

- **Reliability (§23, §37):** `services/reliability/retry.py:28` bounded `3×2s×2.0 capped 30s`, `quarantine.py:5` `s3://.../quarantine/`, `dlq.py:12` `maxReceiveCount 5`, `finalizer/handler.py:14` `PUBLISHED` only if all `SUCCEEDED` + outputs exist. 6 injection tests.
- **Observability (§25):** `services/observability/metrics.py:14` EMF, `alarm_config.py:1` 6 alarms (`SQS-Backlog 1000`, `DLQ-Growth 0`, `SFN-Failures 5`, `ECS-Failures 5`, `Lambda-Errors 10`, `DQ-Failures 5`), `monitoring/dashboard.json:1` 6 widgets (`Assets Today`, `Success %`, `Duration`, `SQS Depth`, `DLQ`, `Active Jobs`), logs `30d`.
- **Security (§26):** `services/security/iam.py:5` least-privilege Table 9 (no `AdministratorAccess`), `services/security/redact.py:8` `AKIA...` redaction, KMS rotation, bucket `block_public_*`, VPC endpoints (`S3`, `DynamoDB`, `ECR`, `Logs`) no NAT, `dev`/`prod` isolated.

## Cost

**10 assets test:** `< $1` + $1 KMS + $3 dashboard if kept. **Idle:** `~$5-7/mo` (KMS $1 + dashboard $3 + logs $1). **100/day ×30:** `~$17/mo` (Fargate $4.5 + Glue $8.7). Parquet `year/month/day` keeps Athena scans cheap.

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 Bootstrap | Repo, Python `3.11+`, harness | ✅ |
| 1 Contracts | Schemas, state machines, versioned | ✅ |
| 2 Domain | Plan registry, idempotency | ✅ |
| 3 Processors | `ffmpeg/Pillow/pypdf`, 3 Dockerfiles | ✅ |
| 4 Workflow | SFN ASL + simulator, finalizer | ✅ |
| 5 Ingestion | S3/EventBridge/SQS/DLQ/Lambda + moto | ✅ |
| 6 Compute | ECS Fargate 5 tasks, IAM, VPC | ✅ |
| 7 State | DynamoDB `PK/SK` + `GSI1`, conditional | ✅ |
| 8 Data | Parquet Snappy, Glue 4 crawlers, Athena | ✅ |
| 9 Reliability | Retries, DLQ, quarantine | ✅ |
| 10 Observability | Metrics, 6 alarms, dashboard | ✅ |
| 11 Security | IAM, KMS, VPC, redaction | ✅ |
| 12 Terraform | 12 modules, `dev`/`prod` `use_lockfile` | ✅ |
| 13 CI/CD | `test→lint→type→docker→tf` | ✅ |
| 14 Optimization | Benchmark sizing | ⬜ Next |
| 15 Portfolio | Diagram, runbook, decisions | ✅ |

## Changelog

- `2026-08-27 v0.2.0` `06c3603` — Frozen, credential-proof (`YOUR_AWS_*` placeholders), 42 tests, `a3fac2d` ECS SFN template (`Cluster` + `NetworkConfiguration` via `private_subnets`), `47c95cc` audio/document tasks, `33affcf` TaskDefinition fix, `c1baf76` real validator (`S3 EventBridge` → `DynamoDB` → `SFN`), `4daf267` SFN logging disabled, `3c58e4e` backend `use_lockfile` (was `dynamodb_table`).
- `2026-08-27 v0.1.0` — Bootstrap, contracts, processors, workflow, data platform.

## License

Private — portfolio reference implementation. No `apply` without replacing `YOUR_AWS_ACCOUNT_ID`/`YOUR_AWS_REGION` in `environments/dev/YOUR_AWS_REGION/main.tf:23`.

