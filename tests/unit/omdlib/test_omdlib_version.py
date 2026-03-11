#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import omdlib
from omdlib.version import main_version, main_versions


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
