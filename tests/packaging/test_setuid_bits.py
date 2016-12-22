import pytest
import os

pytestmark = pytest.mark.packaging

def version_path():
    path = os.environ.get("VERSION_PATH")
    if not path:
        raise Exception("VERSION_PATH environment variable pointing to the version "
                        "directory (e.g. /bauwelt/download/2016.12.22) is missing")
    return path


def test_setuid_bits():
    print version_path()
    print os.listdir(version_path())


def test_files_not_in_version_path():
    pass
