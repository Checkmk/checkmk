# encoding: utf-8

import pytest  # type: ignore[import]
from pathlib2 import Path

import cmk.utils.paths
import cmk.gui.backup as backup
import cmk.gui.wato as wato


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


def test_backup_key_create_web(register_builtin_html, site, monkeypatch):
    store_path = Path(cmk.utils.paths.default_config_dir, "backup_keys.mk")

    assert not store_path.exists()
    mode = wato.ModeBackupEditKey()

    # First create a backup key
    mode._create_key({
        "alias": u"älias",
        "passphrase": "passphra$e",
    })

    assert store_path.exists()

    # Then test key existence
    test_mode = wato.ModeBackupEditKey()
    keys = test_mode.load()
    assert len(keys) == 1

    assert store_path.exists()
    store_path.unlink()
