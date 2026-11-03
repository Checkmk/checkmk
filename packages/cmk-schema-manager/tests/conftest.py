#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(name="omd_root")
def fixture_omd_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture(name="registered_fixture_databases")
def fixture_registered_fixture_databases(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make the databases in schema_migrations_fixture discoverable."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent / "schema_migrations_fixture"))
    imported_before = set(sys.modules)
    yield
    for name in set(sys.modules) - imported_before:
        if name.startswith("cmk.schema_migrations"):
            del sys.modules[name]
