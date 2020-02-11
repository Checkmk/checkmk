import pytest  # type: ignore[import]
import testlib


@pytest.fixture(scope="module")
def inventory_plugin_manager():
    return testlib.InventoryPluginManager()


@pytest.fixture(scope="module")
def check_manager():
    return testlib.CheckManager()
