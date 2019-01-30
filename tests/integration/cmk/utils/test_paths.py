import os

import cmk.utils.paths


def _check_paths(root):
    for var, value in cmk.utils.paths.__dict__.iteritems():
        if not var.startswith("_") and var not in ('Path', 'os'):
            assert isinstance(value, str)
            assert value.startswith(root)


def test_paths_in_site(site):
    _check_paths(site.root)


def test_paths_in_omd_root(monkeypatch):
    omd_root = '/omd/sites/dingeling'
    with monkeypatch.context() as m:
        m.setitem(os.environ, 'OMD_ROOT', omd_root)
        reload(cmk.utils.paths)
        _check_paths(omd_root)
    reload(cmk.utils.paths)
