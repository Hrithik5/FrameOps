# Runbook

## Local Development

```bash
pip install -e ".[dev]"
make all
pytest tests/integration/test_e2e.py -v
```

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Duplicate workflow | `services/processor/idempotency.py` deterministic `asset_id` + DynamoDB conditional | Ensure `attribute_not_exists(PK)` |
| Thumbnail unknown extension | `services/processor/thumbnail.py` handles `s3://.../output` with no suffix → JPEG default | Fixed in 6b4d3e3 |
| Parquet not queryable | Partition `year/month/day` + Snappy — query via DuckDB `read_parquet` | `services/metadata/parquet_writer.py` |
| DLQ growing | CloudWatch alarm `FrameOps-DLQ-Growth` | Check `tests/integration/test_reliability.py` — 5 receives → DLQ |
| Secrets in logs | `services/security/redact.py` | `redact_dict` / `redact_string` |

## Deployment

1. `terraform init` in `environments/dev/ap-south-1` (backend S3 + DynamoDB lock)
2. `terraform plan` → review
3. `terraform apply` (dev). Prod requires manual approval per `.github/workflows/ci.yml`.
4. Verify: upload to `s3://frameops-assets-dev/raw/video/<id>/source.mp4` → check Step Functions execution → DynamoDB `frameops-assets-dev` → `s3://frameops-data-dev/asset_metadata/`.

## Rollback

`terraform apply -target` previous commit; images are immutable versioned tags.

## Known Limitations

- Real ffmpeg only in Fargate Dockerfiles; local transcode is copy-stub.
- Athena → DuckDB locally.
- NAT vs VPC endpoints: dev uses endpoints to avoid NAT cost (Spec §44).
