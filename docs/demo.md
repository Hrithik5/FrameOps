# Demo Scenarios

## 1. Video (Spec §38)
```
raw/video/asset-123/source.mp4 → EventBridge → SQS → Lambda → Step Functions
  → Parallel: Metadata | 1080p | Thumbnail (Fargate)
  → Finalize → PUBLISHED
  → processed/video/asset-123/{1080p.mp4,thumbnail.jpg,metadata.json}
```

## 2. Image
```
raw/image/asset-456/source.jpg → metadata + resize + thumbnail → publish
pytest tests/integration/test_workflow.py -v
```

## 3. Audio
```
raw/audio/asset-789/source.mp3 → metadata + normalize → publish
```

## 4. PDF
```
raw/document/asset-999/source.pdf → integrity (pypdf) + metadata_pages → publish
```

## 5. Duplicate → Idempotent
```
Same ASSET_CREATED twice → one DynamoDB ASSET#id → one Step Functions execution
pytest tests/integration/test_ingestion.py::test_duplicate_event_idempotent
```

## 6. Corrupt → Quarantine
```
Corrupt PDF → permanent failure → s3://frameops-assets-dev/quarantine/<id>/
pytest tests/integration/test_reliability.py
```

## 7. Burst → SQS absorbs
Spec §30: 20,000/10m → SQS buffers, workers at bounded concurrency (10 dev).

## 8. E2E → Lake → Athena
```
pytest tests/integration/test_e2e.py -v
# writes Parquet Snappy year/month/day → DuckDB query simulates Athena
```
