import pytest

import cmk.gui.backup as backup


@pytest.mark.parametrize("path, expected", [
    ("/", True),
    ("/a", True),
    ("/a/", True),
    ("/a/b", True),
    ("a/b", False),
    ("/a//", False),
    ("/a//b", False),
    ("/a/.", False),
    ("/a/./b", False),
    ("/a/..", False),
    ("/a/b/../../etc/shadow", False),
])
def test_is_canonical(monkeypatch, path, expected):
    monkeypatch.setattr("os.getcwd", lambda: '/test')
    monkeypatch.setattr("os.path.islink", lambda x: False)

    assert backup.is_canonical(path) == expected
