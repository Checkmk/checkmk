# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import hashlib
import pytest  # type: ignore
from testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def mk_docker():
    return import_module("agents/plugins/mk_docker.py")


PLUGIN_CHECKSUMS = {
    '0.1': '41a238d0d48c20242bb9482156e6ad00',
}


def test_docker_plugin_version(mk_docker):
    with open(mk_docker.__file__.rstrip('c')) as source:
        md5 = hashlib.md5(source.read()).hexdigest()
    assert md5 == PLUGIN_CHECKSUMS.get(mk_docker.VERSION), """
    Plugin source code has changed.
    If your changes are compatible to previous versions,
    put the new md5 sum of the plugin into PLUIGIN_CHECKSUMS.
    If your change is incompatible, increase the mk_docker.VERSION
    and put a new entry into PLUIGIN_CHECKSUMS.
    """
