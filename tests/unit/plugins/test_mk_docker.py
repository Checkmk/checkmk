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
    '0.1': '2e03d077fbefb3b10a51600aa23d2154',
}


def test_docker_plugin_version():
    with open(mk_docker.__file__) as source:
        md5 = hashlib.md5(source.read()).hexdigest()
    assert md5 == PLUGIN_CHECKSUMS.get(mk_docker.VERSION), """
    Plugin source code has changed.
    If your changes are compatible to previous versions,
    add the new md5 sum of the plugin to the corresponding
    list in PLUIGIN_CHECKSUMS.
    If your change is incompatible, increase the mk_docker.VERSION
    and start a new list to PLUIGIN_CHECKSUMS.
    """
