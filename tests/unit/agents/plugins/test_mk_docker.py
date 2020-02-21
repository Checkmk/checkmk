# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import hashlib
import pytest  # type: ignore[import]
from testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def mk_docker():
    return import_module("agents/plugins/mk_docker.py")


PLUGIN_CHECKSUMS = {
    '0.1': '5b3d6f5ba3d3d9655397ad8075090b69',
}


def test_docker_plugin_version(mk_docker):
    with open(mk_docker.__file__.rstrip('c')) as source:
        md5 = hashlib.md5(source.read()).hexdigest()
    assert md5 == PLUGIN_CHECKSUMS.get(mk_docker.VERSION), """
    Plugin source code has changed.
    If your changes are compatible to previous versions,
    put the new md5 sum of the plugin into PLUGIN_CHECKSUMS.
    If your change is incompatible, increase the mk_docker.VERSION
    and put a new entry into PLUGIN_CHECKSUMS.
    """
