#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

from cmk.werks.tool import load_werk
from cmk.werks.tool.config import RuntimeConfiguration
from cmk.werks.tool.models import EditionV3, WerkV3
from cmk.werks.tool.utils import (
    load_precompiled_werks_file,
    resolve_version,
    sort_by_version_and_component,
)

from ._werk_files import werk_text


def _werk(werk_id: int, *, version: str, component: str = "core") -> WerkV3:
    return load_werk(
        file_content=werk_text(version=version, component=component), file_name=f"{werk_id}.md"
    )


def test_a_precompiled_v2_werk_is_loaded_with_its_v3_edition(tmp_path: Path) -> None:
    precompiled = tmp_path / "werks"
    precompiled.write_text(
        json.dumps(
            {
                "1": {
                    "__version__": "2",
                    "id": 1,
                    "class": "fix",
                    "component": "core",
                    "level": 1,
                    "date": "2026-01-01T00:00:00+00:00",
                    "compatible": "yes",
                    "edition": "cee",
                    "description": "<p>A description.</p>",
                    "title": "A werk title",
                    "version": "2.2.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert load_precompiled_werks_file(precompiled)[1].edition is EditionV3.PRO


def test_werks_are_sorted_newest_version_first() -> None:
    werks = [_werk(1, version="2.4.0"), _werk(2, version="2.5.0")]

    assert [werk.id for werk in sort_by_version_and_component(werks)] == [2, 1]


def test_werks_of_one_version_are_sorted_by_component_title() -> None:
    werks = [
        _werk(1, version="2.5.0", component="core"),
        _werk(2, version="2.5.0", component="checks"),
    ]

    assert [werk.id for werk in sort_by_version_and_component(werks)] == [2, 1]


def test_an_unreleased_version_comes_from_defines_make(tmp_path: Path) -> None:
    (tmp_path / "defines.make").write_text("VERSION := 2.5.0b1\n", encoding="utf-8")

    assert resolve_version(RuntimeConfiguration(tmp_path), None) == "2.5.0b1"
