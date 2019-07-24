# -*- encoding: utf-8
# pylint: disable=protected-access
import os
import sys
import hashlib
#import pytest
from testlib import cmk_path  # pylint: disable=import-error

sys.path.insert(0, os.path.join(cmk_path(), 'agents', 'plugins'))

import mk_docker  # pylint: disable=import-error,wrong-import-position

PLUGIN_CHECKSUMS = {
    '0.1': 'c162e333908cc6f13de56b837aa95c28',
}


def test_docker_plugin_version():
    with open(mk_docker.__file__.rstrip('c')) as source:
        md5 = hashlib.md5(source.read()).hexdigest()
    assert md5 == PLUGIN_CHECKSUMS.get(mk_docker.VERSION), """
    Plugin source code has changed.
    If your changes are compatible to previous versions,
    put the new md5 sum of the plugin into PLUIGIN_CHECKSUMS.
    If your change is incompatible, increase the mk_docker.VERSION
    and put a new entry into PLUIGIN_CHECKSUMS.
    """
