import pytest  # type: ignore
import testlib


@pytest.fixture(scope="module")
def inventory_plugin_manager():
    return testlib.InventoryPluginManager()
