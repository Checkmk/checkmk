import pytest
import os

from cmk.exceptions import MKGeneralException
import cmk.paths

def _all_path_names():
    import cmk.paths
    names = []
    for name in dir(cmk.paths):
        if name in [ "MKGeneralException", "os" ] or name[0] == "_":
            continue
        names.append(name)
    return names


def test_paths_in_site(site):
    for var_name in _all_path_names():
        value = cmk.paths.__dict__[var_name]
        assert value is not None
        assert type(value) == str
        assert value.startswith(site.root)


def test_no_path_variable_none(monkeypatch):
    monkeypatch.setitem(os.environ, 'OMD_ROOT', '/omd/sites/dingeling')
    reload(cmk.paths)

    for var_name in _all_path_names():
        value = cmk.paths.__dict__[var_name]
        assert value is not None
        assert type(value) == str
        assert value.startswith("/omd/sites/dingeling")

    monkeypatch.undo()
    reload(cmk.paths)
