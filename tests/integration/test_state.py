from unittest.mock import MagicMock

from services.processor.state import put_asset_if_not_exists


def test_conditional_write_prevents_duplicate():
    table = MagicMock()
    # First call succeeds
    table.put_item.return_value = {}
    assert put_asset_if_not_exists(table, {"PK": "ASSET#a1", "SK": "ASSET#a1"}) is True
    # Second call simulates ConditionalCheckFailed
    table.put_item.side_effect = Exception("ConditionalCheckFailedException")
    assert put_asset_if_not_exists(table, {"PK": "ASSET#a1", "SK": "ASSET#a1"}) is False
