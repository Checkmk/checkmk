#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

import pytest

from omdlib.sites import is_disabled, main_sites


def _strip_ansi(s: str) -> str:
    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", s)


def test_main_sites(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")

    # Empty site directory
    tmp_path.joinpath("omd/sites/empty").mkdir(parents=True)
    tmp_path.joinpath("omd/apache").mkdir(parents=True)
    tmp_path.joinpath("omd/apache/empty.conf").open("w").close()

    # Site with version
    tmp_path.joinpath("omd/sites/xyz").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/xyz/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/apache/xyz.conf").open("w").close()

    # Site with not existing version
    tmp_path.joinpath("omd/sites/broken").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/broken/version").symlink_to("../../versions/1.0.0")
    tmp_path.joinpath("omd/apache/broken.conf").open("w").close()

    # Site with default version
    tmp_path.joinpath("omd/sites/default").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/default/version").symlink_to("../../versions/1.6.0p4")
    tmp_path.joinpath("omd/apache/default.conf").open("w").close()

    # Disabled site
    tmp_path.joinpath("omd/sites/disabled").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/disabled/version").symlink_to("../../versions/1.6.0p4")

    main_sites(object(), object(), object(), [], {}, tmp_path / "omd/")

    stdout = _strip_ansi(capsys.readouterr()[0])
    assert (
        stdout == "broken           1.0.0             \n"
        "default          1.6.0p4          default version \n"
        "disabled         1.6.0p4          default version, disabled \n"
        "empty            (none)           empty site dir \n"
        "xyz              1.2.3p4           \n"
    )


def test_is_disabled(tmp_path: Path) -> None:
    apache_config_existing = tmp_path / "dingeling.conf"
    apache_config_existing.touch()
    assert not is_disabled(apache_config_existing)

    assert is_disabled(tmp_path / "dingelang.conf")
