import os
from pathlib2 import Path

import cmk.utils.paths

pathlib_paths = [
    "discovered_host_labels_dir",
    "piggyback_dir",
    "piggyback_source_dir",
]


def _check_paths(root):
    for var, value in cmk.utils.paths.__dict__.iteritems():
        if not var.startswith("_") and var not in ('Path', 'os'):
            if var in pathlib_paths:
                assert isinstance(value, Path)
                assert str(value).startswith(root)
            else:
                assert isinstance(value, str)
                assert value.startswith(root)


def test_paths_in_site(site):
    _check_paths(site.root)


def test_paths_in_omd_root(monkeypatch):
    omd_root = '/omd/sites/dingeling'
    try:
        with monkeypatch.context() as m:
            m.setitem(os.environ, 'OMD_ROOT', omd_root)
            reload(cmk.utils.paths)
            _check_paths(omd_root)
    finally:
        reload(cmk.utils.paths)
