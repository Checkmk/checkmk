
import sys
import pytest

import cmk
import testlib


@pytest.fixture(scope="module")
def check_manager():
    manager = testlib.CheckManager()
    manager.load()
    return manager
