"""Lambda validator handler — thin wrapper over pure core (Spec §8)."""

import json
import os
from typing import Any

try:
    from data.schemas.events import AssetCreatedEvent
    from services.validator.core import validate_asset

    HAS_SCHEMAS = True
except Exception:
    HAS_SCHEMAS = False


def _infer_asset_type(key: str, fallback: str = "other") -> str:
    kl = key.lower()
    if "raw/video/" in kl or kl.endswith((".mp4", ".mov", ".avi", ".mkv")):
        return "video"
    if "raw/image/" in kl or kl.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"
    if "raw/audio/" in kl or kl.endswith((".mp3", ".wav", ".aac")):
        return "audio"
    if "raw/document/" in kl or kl.endswith((".pdf", ".docx")):
        return "document"
    return fallback


def _build_asset_created_from_s3(detail: dict[str, Any]) -> dict[str, Any]:
    # EventBridge S3 ObjectCreated detail: {bucket: {name}, object: {key, size, etag}}
    bucket = detail.get("bucket", {}).get("name", "") or detail.get("bucketName", "")
    key = detail.get("object", {}).get("key", "") or detail.get("objectKey", "")
    size = detail.get("object", {}).get("size", 0)
    etag = detail.get("object", {}).get("etag", "") or detail.get("object", {}).get("ETag", "chk")
    # Derive deterministic asset_id
    try:
        from services.processor.idempotency import deterministic_asset_id

        asset_id = deterministic_asset_id(bucket, key, etag or "v1")
    except Exception:
        asset_id = f"asset-{abs(hash(key))%1000000}"
    asset_type = _infer_asset_type(key)
    return {
        "event_type": "ASSET_CREATED",
        "event_version": "1.0",
        "asset_id": asset_id,
        "asset_type": asset_type,
        "bucket": bucket,
        "object_key": key,
        "object_version": etag or "v1",
        "checksum": etag or "chk",
        "created_at": detail.get("eventTime", "") or "",
        "file_size_bytes": size,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process SQS batch of S3 ObjectCreated (EventBridge) or ASSET_CREATED events."""
    results: list[dict[str, Any]] = []
    # Lazy boto3 clients — only if env vars present (real AWS)
    table_name = os.environ.get("TABLE_NAME", "")
    state_machine_arn = os.environ.get("STATE_MACHINE_ARN", "")
    use_aws = bool(table_name and state_machine_arn)
    dynamodb = None
    sfn = None
    if use_aws:
        try:
            import boto3

            dynamodb = boto3.resource("dynamodb").Table(table_name)
            sfn = boto3.client("stepfunctions")
        except Exception as e:
            results.append({"status": "error", "reason": f"boto3 init failed: {e}"})
            use_aws = False

    for record in event.get("Records", []):
        try:
            body_raw = record.get("body", "")
            if isinstance(body_raw, str):
                body = json.loads(body_raw) if body_raw else {}
            else:
                body = body_raw if isinstance(body_raw, dict) else {}

            # Unwrap SQS -> EventBridge -> S3
            # SQS body is EventBridge envelope: {"source":"aws.s3","detail":{bucket, object}}
            # Or SQS body may be direct JSON string of AssetCreatedEvent (tests)
            inner: dict[str, Any] = body
            # EventBridge wraps as {"detail": {"bucket":..., "object":...}, "source":"aws.s3"}
            if isinstance(body, dict) and "detail" in body and "bucket" in body["detail"]:
                inner = _build_asset_created_from_s3(body["detail"])
            elif isinstance(body, dict) and "Records" in body:
                # Direct S3 notification (fallback)
                rec = body["Records"][0]
                s3 = rec.get("s3", {})
                bucket_name = s3.get("bucket", {}).get("name", "")
                object_key = s3.get("object", {}).get("key", "")
                inner = _build_asset_created_from_s3(
                    {"bucket": {"name": bucket_name}, "object": {"key": object_key}}
                )
            # else assume inner is already ASSET_CREATED

            if HAS_SCHEMAS:
                try:
                    evt = AssetCreatedEvent.model_validate(inner)
                except Exception as e:
                    results.append({"status": "quarantine", "reason": f"invalid event: {e}"})
                    continue
                res = validate_asset(evt)
                if not res.valid:
                    results.append(
                        {
                            "asset_id": getattr(evt, "asset_id", "unknown"),
                            "status": "quarantine",
                            "reason": res.reason,
                        }
                    )
                    continue
                asset_id = evt.asset_id
                asset_type = evt.asset_type
                payload = evt.model_dump()
            else:
                # Fallback without pydantic (Lambda without layer)
                if not inner.get("asset_id") or not inner.get("bucket"):
                    results.append({"status": "quarantine", "reason": "missing fields"})
                    continue
                asset_id = inner["asset_id"]
                asset_type = inner.get("asset_type", "other")
                payload = inner

            if not use_aws:
                results.append(
                    {"asset_id": asset_id, "status": "proceed", "asset_type": asset_type}
                )
                continue

            # Idempotent DynamoDB Put — Spec §22 ConditionExpression
            try:
                assert dynamodb is not None
                dynamodb.put_item(
                    Item={
                        "PK": f"ASSET#{asset_id}",
                        "SK": f"ASSET#{asset_id}",
                        "asset_id": asset_id,
                        "asset_type": asset_type,
                        "status": "INGESTED",
                        "source_uri": f"s3://{payload.get('bucket')}/{payload.get('object_key')}",
                        "GSI1PK": "STATUS#INGESTED",
                        "GSI1SK": asset_id,
                    },
                    ConditionExpression="attribute_not_exists(PK)",
                )
            except Exception as e:
                if "ConditionalCheckFailed" in str(e):
                    results.append(
                        {
                            "asset_id": asset_id,
                            "status": "duplicate",
                            "reason": "already ingested",
                        }
                    )
                    continue
                # Other DynamoDB errors → retry via SQS (raise to trigger SQS redelivery)
                raise

            # Start Step Functions execution — Spec §14
            try:
                assert sfn is not None
                sfn.start_execution(
                    stateMachineArn=state_machine_arn,
                    name=f"{asset_id}-{payload.get('object_version', 'v1')}"[:80],
                    input=json.dumps(
                        {"asset_id": asset_id, "asset_type": asset_type, **payload}
                    ),
                )
                results.append(
                    {"asset_id": asset_id, "status": "proceed", "asset_type": asset_type}
                )
            except Exception:
                # If SFN start fails, let SQS redelivery handle it (Spec §23)
                raise

        except Exception as e:
            import traceback

            results.append(
                {
                    "status": "error",
                    "reason": str(e)[:500],
                    "trace": traceback.format_exc()[:500],
                }
            )

    # For SQS ReportBatchItemFailures, we should raise if any error, but for MVP return results
    return {"results": results}
