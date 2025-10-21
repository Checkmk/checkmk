from typing import Any

from cmk.agent_based.v2 import InventoryResult, TableRow


def get_inventory_value(inventory: InventoryResult, key: str) -> Any:
    for row in inventory:
        assert isinstance(row, TableRow)
        if row.key_columns["information"] == key:
            return row.inventory_columns["value"]
