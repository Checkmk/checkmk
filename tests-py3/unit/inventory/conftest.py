import pytest  # type: ignore[import]
import testlib  # type: ignore[import]

# TODO Python 3: Copied conftest from orig conftest file (Python 2)
# If new fixtures are implemented, don't forget to port them to
#   tests/unit/inventory/conftest.py


@pytest.fixture(scope="module")
def inventory_plugin_manager():
    return testlib.InventoryPluginManager()


@pytest.fixture(scope="module")
def check_manager():
    return testlib.CheckManager()
