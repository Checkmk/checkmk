#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.paths

import cmk.gui.backup as backup
import cmk.gui.wato as wato
from cmk.gui.logged_in import user


@pytest.mark.parametrize(
    "path, expected",
    [
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
    ],
)
def test_is_canonical(monkeypatch, path, expected) -> None:
    monkeypatch.setattr("os.getcwd", lambda: "/test")
    monkeypatch.setattr("os.path.islink", lambda x: False)

    assert backup.is_canonical(path) == expected


@pytest.mark.usefixtures("request_context")
def test_backup_key_create_web(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user, "id", "dingdöng")
    store_path = Path(cmk.utils.paths.default_config_dir, "backup_keys.mk")

    assert not store_path.exists()
    mode = wato.ModeBackupEditKey()

    # First create a backup key
    mode._create_key(alias="älias", passphrase="passphra$e")

    assert store_path.exists()

    # Then test key existence
    test_mode = wato.ModeBackupEditKey()
    keys = test_mode.key_store.load()
    assert len(keys) == 1

    assert store_path.exists()
    store_path.unlink()
