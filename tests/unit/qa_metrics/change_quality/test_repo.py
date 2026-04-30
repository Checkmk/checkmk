#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from pathlib import Path

import pytest

from tests.qa_metrics.change_quality.repo import read_branch_version


def test_read_branch_version_extracts_value(tmp_path: Path) -> None:
    (tmp_path / "defines.make").write_text(
        "# preamble\n"
        "VERSION            := 2.6.0-2026.04.29\n"
        "BRANCH_VERSION     := 2.6.0\n"
        "EDITION            := raw\n",
        encoding="utf-8",
    )
    assert read_branch_version(tmp_path) == "2.6.0"


def test_read_branch_version_handles_plain_assignment(tmp_path: Path) -> None:
    (tmp_path / "defines.make").write_text("BRANCH_VERSION = 2.4.0\n", encoding="utf-8")
    assert read_branch_version(tmp_path) == "2.4.0"


def test_read_branch_version_raises_when_missing(tmp_path: Path) -> None:
    (tmp_path / "defines.make").write_text("# no branch version here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="BRANCH_VERSION not found"):
        read_branch_version(tmp_path)
