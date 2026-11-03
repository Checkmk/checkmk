#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.schema_manager._paths import db_path, omd_root


def test_omd_root_reads_the_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_ROOT", "/omd/sites/mysite")

    assert omd_root() == Path("/omd/sites/mysite")


def test_omd_root_is_empty_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMD_ROOT", raising=False)

    assert omd_root() == Path()


def test_db_path_is_under_var_check_mk_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_ROOT", "/omd/sites/mysite")

    assert db_path("oauth") == Path("/omd/sites/mysite/var/check_mk/oauth/db.sqlite3")
