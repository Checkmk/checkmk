#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from pathlib import Path

from cmk.werks.site import find_werk, load
from cmk.werks.site.acknowledgement import (
    load_acknowledgements,
    save_acknowledgements,
    write_unacknowledged_werks,
)
from cmk.werks.tool.models import Class, Compatibility, EditionV3, Level, WerkV3
from cmk.werks.tool.utils import write_precompiled_werks

WERK_V1 = {
    "15374": {
        "class": "fix",
        "component": "rest-api",
        "date": 1676973331,
        "level": 1,
        "title": "crash-reporting: Improve crash reporting information",
        "version": "2.2.0b3",
        "compatible": "incomp",
        "edition": "cre",
        "knowledge": "doc",
        "state": "unknown",
        "id": 15374,
        "targetversion": None,
        "description": [
            "In the event of a crash when calling the rest-api, having more",
            "useful information helps find the root cause which helps",
            "fix the issue quicker. This werk introduces the changes to",
            "the data returned in a crash report.",
            "",
            "",
        ],
    }
}


def _werk(werk_id: int, *, version: str = "2.5.0", title: str = "Some werk") -> WerkV3:
    return WerkV3(
        id=werk_id,
        class_=Class.FIX,
        component="core",
        level=Level.LEVEL_1,
        date=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        compatible=Compatibility.NOT_COMPATIBLE,
        edition=EditionV3.COMMUNITY,
        description="<p>description</p>",
        title=title,
        version=version,
    )


def _shipped_werks_dir(tmp_path: Path, werks: dict[int, WerkV3]) -> Path:
    base_dir = tmp_path / "share"
    base_dir.mkdir()
    write_precompiled_werks(base_dir / "werks", werks)
    return base_dir


def test_a_shipped_v1_werk_is_loaded_as_a_v3_werk(tmp_path: Path) -> None:
    werks_folder = tmp_path / "werks_folder"
    werks_folder.mkdir()
    not_existing = tmp_path / "asdasd_not_existing"
    with (werks_folder / "werks").open("w") as fo:
        json.dump(WERK_V1, fo)

    result = load(
        base_dir=werks_folder,
        unacknowledged_werks_json=not_existing,
        acknowledged_werks_mk=not_existing,
    )

    assert result == {
        15374: WerkV3(
            werk_version="3",
            id=15374,
            class_=Class.FIX,
            component="rest-api",
            level=Level.LEVEL_1,
            date=datetime.datetime(2023, 2, 21, 9, 55, 31, tzinfo=datetime.UTC),
            compatible=Compatibility.NOT_COMPATIBLE,
            edition=EditionV3.COMMUNITY,
            description="<p>In the event of a crash when calling the rest-api, having more\n"
            "useful information helps find the root cause which helps\n"
            "fix the issue quicker. This werk introduces the changes to\n"
            "the data returned in a crash report.</p>",
            title="crash-reporting: Improve crash reporting information",
            version="2.2.0b3",
        )
    }


def test_werks_of_every_shipped_file_are_loaded(tmp_path: Path) -> None:
    base_dir = _shipped_werks_dir(tmp_path, {1: _werk(1)})
    write_precompiled_werks(base_dir / "werks-pro", {2: _werk(2)})

    result = load(
        base_dir=base_dir,
        unacknowledged_werks_json=tmp_path / "missing.json",
        acknowledged_werks_mk=tmp_path / "missing.mk",
    )

    assert sorted(result) == [1, 2]


def test_an_unacknowledged_werk_of_a_previous_version_is_loaded(tmp_path: Path) -> None:
    base_dir = _shipped_werks_dir(tmp_path, {1: _werk(1)})
    unacknowledged_werks_json = tmp_path / "unacknowledged_werks.json"
    write_unacknowledged_werks(
        {2: _werk(2, version="2.4.0")}, unacknowledged_werks_json=unacknowledged_werks_json
    )

    result = load(
        base_dir=base_dir,
        unacknowledged_werks_json=unacknowledged_werks_json,
        acknowledged_werks_mk=tmp_path / "missing.mk",
    )

    assert sorted(result) == [1, 2]


def test_an_acknowledged_werk_of_a_previous_version_is_not_loaded(tmp_path: Path) -> None:
    base_dir = _shipped_werks_dir(tmp_path, {1: _werk(1)})
    unacknowledged_werks_json = tmp_path / "unacknowledged_werks.json"
    acknowledged_werks_mk = tmp_path / "acknowledged_werks.mk"
    write_unacknowledged_werks(
        {2: _werk(2, version="2.4.0")}, unacknowledged_werks_json=unacknowledged_werks_json
    )
    save_acknowledgements([2], acknowledged_werks_mk=acknowledged_werks_mk)

    result = load(
        base_dir=base_dir,
        unacknowledged_werks_json=unacknowledged_werks_json,
        acknowledged_werks_mk=acknowledged_werks_mk,
    )

    assert sorted(result) == [1]


def test_a_shipped_werk_keeps_the_version_it_was_first_seen_with(tmp_path: Path) -> None:
    base_dir = _shipped_werks_dir(tmp_path, {1: _werk(1, version="2.5.0", title="New title")})
    unacknowledged_werks_json = tmp_path / "unacknowledged_werks.json"
    write_unacknowledged_werks(
        {1: _werk(1, version="2.4.0", title="Old title")},
        unacknowledged_werks_json=unacknowledged_werks_json,
    )

    result = load(
        base_dir=base_dir,
        unacknowledged_werks_json=unacknowledged_werks_json,
        acknowledged_werks_mk=tmp_path / "missing.mk",
    )

    assert (result[1].title, result[1].version) == ("New title", "2.4.0")


def test_saved_acknowledgements_are_loaded_back(tmp_path: Path) -> None:
    acknowledged_werks_mk = tmp_path / "acknowledged_werks.mk"
    save_acknowledgements([3, 1, 2], acknowledged_werks_mk=acknowledged_werks_mk)

    assert load_acknowledgements(acknowledged_werks_mk=acknowledged_werks_mk) == {1, 2, 3}


def test_no_werk_is_acknowledged_without_an_acknowledgements_file(tmp_path: Path) -> None:
    assert load_acknowledgements(acknowledged_werks_mk=tmp_path / "missing.mk") == set()


def test_the_werk_with_the_requested_id_is_found() -> None:
    assert find_werk([_werk(1), _werk(2)], 2) == _werk(2)


def test_an_unknown_werk_is_not_found() -> None:
    assert find_werk([_werk(1)], 2) is None
