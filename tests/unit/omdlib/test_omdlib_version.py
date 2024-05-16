#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest

import omdlib
from omdlib.version import (
    default_version,
    main_version,
    main_versions,
    omd_versions,
    version_exists,
    version_from_site_dir,
)


def test_main_version_of_omd_tool(capsys: pytest.CaptureFixture[str]) -> None:
    main_version(object(), object(), object(), [], {})

    stdout = capsys.readouterr()[0]
    assert stdout == f"OMD - Open Monitoring Distribution Version {omdlib.__version__}\n"


def test_main_version_root_not_existing_site(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="No such site: testsite"):
        main_version(object(), object(), object(), ["testsite"], {}, tmp_path / "omd")


def test_main_version_root_specific_site_broken_version(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    with pytest.raises(SystemExit, match="Failed to determine site version"):
        main_version(object(), object(), object(), ["testsite"], {}, tmp_path / "omd")


def test_main_version_root_specific_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/testsite/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    main_version(object(), object(), object(), ["testsite"], {}, tmp_path / "omd")

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_specific_site_bare(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/testsite/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    main_version(object(), object(), object(), ["testsite"], {"bare": None}, tmp_path / "omd")

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n"


def test_main_versions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")
    main_versions(object(), object(), object(), [], {}, tmp_path / "omd/versions")

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4 (default)\n"


def test_main_versions_bare(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")
    main_versions(object(), object(), object(), [], {"bare": None}, tmp_path / "omd/versions")

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4\n"


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
