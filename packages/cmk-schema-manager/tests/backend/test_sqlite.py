#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.schema_manager.backend.sqlite import Sqlite


@pytest.mark.usefixtures("omd_root")
def test_exists_is_false_when_the_file_is_absent() -> None:
    assert Sqlite().exists("db") is False


@pytest.mark.usefixtures("omd_root")
def test_exists_is_true_when_the_file_is_present() -> None:
    db_path = Sqlite().path("db")
    db_path.parent.mkdir(parents=True)
    db_path.touch()

    assert Sqlite().exists("db") is True


def test_path_resolves_the_name_under_var_check_mk_at_call_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = Sqlite()
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))

    assert backend.path("oauth") == tmp_path / "var" / "check_mk" / "oauth" / "db.sqlite3"
