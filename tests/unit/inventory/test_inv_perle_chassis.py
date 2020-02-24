import pytest  # type: ignore[import]

# TODO: Change back to fixture (see conftest.py) after Python 3 migration
from inventory_testlib import inventory_plugin_manager


@pytest.mark.parametrize(
    'info, inventory_data',
    [([["MODEL", "SERIAL", "BOOTLOADER", "FW", "_ALARMS", "_DIAGSTATE", "_TEMP_STR"]], {
        "serial": "SERIAL",
        "model": "MODEL",
        "bootloader": "BOOTLOADER",
        "firmware": "FW"
    })])
def test_inv_perle_chassis(info, inventory_data):
    inv_plugin = inventory_plugin_manager().get_inventory_plugin('perle_chassis')
    inventory_tree_data, status_tree_data = inv_plugin.run_inventory(info)

    assert status_tree_data == {}

    path = "hardware.chassis."
    assert path in inventory_tree_data

    node_inventory_data = inventory_tree_data[path]
    assert sorted(node_inventory_data.items()) == sorted(inventory_data.items())
