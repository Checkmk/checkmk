#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.utils.crypto.password import Password
from cmk.utils.type_defs import UserId

import cmk.gui.wato as wato
from cmk.gui.logged_in import user


@pytest.mark.usefixtures("request_context")
def test_backup_key_create_web(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "id", UserId("dingdöng"))
        store_path = Path(cmk.utils.paths.default_config_dir, "backup_keys.mk")

        assert not store_path.exists()
        mode = wato.ModeBackupEditKey()

        # First create a backup key
        mode._create_key(alias="älias", passphrase=Password("passphra$e"))

        assert store_path.exists()

        # Then test key existence
        test_mode = wato.ModeBackupEditKey()
        keys = test_mode.key_store.load()
        assert len(keys) == 1

        assert store_path.exists()
        store_path.unlink()
