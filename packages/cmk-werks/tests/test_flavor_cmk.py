#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.werks.flavor.cmk import CmkFlavor
from cmk.werks.tool.flavor import current_version


def _write_defines_make(tmp_path: Path, content: str) -> None:
    (tmp_path / "defines.make").write_text(content, encoding="utf-8")


def test_the_version_is_read_from_defines_make(tmp_path: Path) -> None:
    _write_defines_make(tmp_path, "EDITION := community\nVERSION := 2.5.0b1\n")

    assert CmkFlavor().read_current_version(tmp_path) == "2.5.0b1"


def test_defines_make_without_a_version_yields_none(tmp_path: Path) -> None:
    _write_defines_make(tmp_path, "EDITION := community\n")

    assert CmkFlavor().read_current_version(tmp_path) is None


def test_a_missing_defines_make_yields_none(tmp_path: Path) -> None:
    assert CmkFlavor().read_current_version(tmp_path) is None


def test_the_current_version_of_the_repository_is_required(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Could not determine the current version"):
        current_version(CmkFlavor(), tmp_path)
