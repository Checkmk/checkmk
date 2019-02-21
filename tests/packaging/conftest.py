import os
import pytest


@pytest.fixture(scope="module")
def version_path():
    path = os.environ.get("VERSION_PATH")
    if not path:
        raise Exception("VERSION_PATH environment variable pointing to the version "
                        "directory (e.g. /bauwelt/download/2016.12.22) is missing")
    return path
