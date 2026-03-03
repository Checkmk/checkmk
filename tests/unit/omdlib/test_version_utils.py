#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path

from omdlib.version_utils import (
    default_version,
    omd_versions,
    version_exists,
    version_from_site_dir,
)


def test_default_version(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/versions").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("2019.12.11.cee")
    assert default_version(tmp_path / "omd/versions") == "2019.12.11.cee"
    assert isinstance(default_version(tmp_path / "omd/versions"), str)


def test_omd_versions(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/versions").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/2019.12.11.cee").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p7").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0i1").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0i10").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.2.0p23").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("2019.12.11.cee")

    assert omd_versions(tmp_path / "omd/versions") == [
        "1.2.0p23",
        "1.6.0i1",
        "1.6.0i10",
        "1.6.0p7",
        "2019.12.11.cee",
    ]


def test_version_exists(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/versions/1.6.0p7").mkdir(parents=True)
    assert version_exists("1.6.0p7", tmp_path / "omd/versions") is True
    assert version_exists("1.6.0p6", tmp_path / "omd/versions") is False


def test_site_context_version(tmp_path: Path) -> None:
    version = "2018.08.11.cee"
    os.symlink(f"../../versions/{version}", tmp_path / "version")
    assert version_from_site_dir(tmp_path) == "2018.08.11.cee"
