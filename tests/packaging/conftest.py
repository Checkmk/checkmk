import os
import pytest


# Packaging tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass


@pytest.fixture(scope="module")
def version_path():
    path = os.environ.get("VERSION_PATH")
    if not path:
        raise Exception("VERSION_PATH environment variable pointing to the version "
                        "directory (e.g. /bauwelt/download/2016.12.22) is missing")
    return path
