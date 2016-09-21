import pytest
import os

from cmk.exceptions import MKGeneralException

def _all_path_names():
    import cmk.paths
    names = []
    for name in dir(cmk.paths):
        if name in [ "MKGeneralException", "os" ] or name[0] == "_":
            continue
        names.append(name)
    return names


def test_without_omd_environment():
    with pytest.raises(MKGeneralException) as e:
        import cmk.paths
    assert "You can only execute this in an OMD site" in "%s" % e


def test_with_omd_environment(monkeypatch):
    monkeypatch.setitem(os.environ, 'OMD_ROOT', '/omd/sites/dingeling')
    import cmk.paths


def test_no_path_variable_none(monkeypatch):
    monkeypatch.setitem(os.environ, 'OMD_ROOT', '/omd/sites/dingeling')
    import cmk.paths
    for var_name in _all_path_names():
        value = cmk.paths.__dict__[var_name]
        assert value != None
        assert type(value) == str
        assert value.startswith("/omd/sites/dingeling")
