"""DynamoDB state helpers — conditional writes for idempotency (Spec §22)."""

from typing import Any

try:
    HAS_BOTO3 = True
except Exception:
    HAS_BOTO3 = False


def put_asset_if_not_exists(table: Any, item: dict[str, Any]) -> bool:
    """Conditional Put: returns True if inserted, False if already exists."""
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
        return True
    except Exception as e:
        # Handle ConditionalCheckFailedException
        if "ConditionalCheckFailed" in str(e) or "conditional" in str(e).lower():
            return False
        raise


def get_asset(table: Any, asset_id: str) -> dict[str, Any] | None:
    pk = f"ASSET#{asset_id}"
    resp = table.get_item(Key={"PK": pk, "SK": pk})
    item = resp.get("Item")
    return item  # type: ignore[no-any-return]


def update_job(table: Any, asset_id: str, job_id: str, status: str, **kwargs: Any) -> None:
    pk = f"ASSET#{asset_id}"
    sk = f"JOB#{job_id}"
    # Simplified update
    expr = "SET #s = :s"
    table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression=expr,
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status},
    )
