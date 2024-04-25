#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.contexts import SiteContext
from omdlib.site_name import sitename_must_be_valid


def test_sitename_must_be_valid_ok(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)
    sitename_must_be_valid(SiteContext("lulu"))


@pytest.mark.parametrize(
    "name,expected_result",
    [
        ("0asd", False),
        ("asd0", True),
        ("", False),
        ("aaaaaaaaaaaaaaaa", True),
        ("aaaaaaaaaaaaaaaaa", False),
    ],
)
def test_sitename_must_be_valid_regex(tmp_path: Path, name: str, expected_result: bool) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    if expected_result:
        sitename_must_be_valid(SiteContext(name))
    else:
        with pytest.raises(SystemExit, match="Invalid site name"):
            sitename_must_be_valid(SiteContext(name))


def test_sitename_must_be_valid_already_exists(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    with pytest.raises(SystemExit, match="already existing"):
        sitename_must_be_valid(SiteContext("lala"))
