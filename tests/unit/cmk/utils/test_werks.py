#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.werks import _load_werk, Werk

WERK = Werk(
    {
        "class": "fix",
        "component": "core",
        "date": 0,
        "level": 1,
        "title": "Some Title",
        "version": "v42.0.0p7",
        "compatible": "comp",
        "edition": "cre",
        "description": [],
    }
)


def write_werk(path: Path, werk_dict: Mapping[str, Any]) -> None:
    with path.open("w") as outfile:
        for key, value in werk_dict.items():
            if key == "description":
                continue
            outfile.write(f"{key}: {value}\n")
        assert isinstance(werk_dict["description"], list)
        outfile.writelines(f"{line}\n" for line in werk_dict["description"])


def test_werk_loading(tmp_path: Path) -> None:
    write_werk(tmp_path / "good", WERK)
    assert json.dumps(WERK, sort_keys=True) == json.dumps(
        _load_werk(tmp_path / "good"), sort_keys=True
    )


def test_werk_loading_missing_field(tmp_path: Path) -> None:
    bad_werk = dict(WERK)
    bad_werk.pop("class")
    write_werk(tmp_path / "bad", bad_werk)
    with pytest.raises(MKGeneralException, match="missing fields: class"):
        _load_werk(tmp_path / "bad")


def test_werk_loading_unknown_field(tmp_path: Path) -> None:
    bad_werk = dict(WERK)
    bad_werk["foo"] = "bar"
    write_werk(tmp_path / "bad", bad_werk)
    with pytest.raises(MKGeneralException, match="unknown werk field foo"):
        _load_werk(tmp_path / "bad")
