#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict

from cmk.ccc.version import __version__, Version
from cmk.flags import load_release_flags, release_field, ReleaseFlagConfig

_REQUIRED_METADATA = ("description", "remove_ticket", "remove_after", "owner")


class _ExampleFlags(BaseModel):
    """Stand-in with a real flag, since ``ReleaseFlagConfig`` may declare none."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    example_flag: Annotated[
        bool,
        release_field(
            description="An example flag.",
            remove_ticket="CMK-00000",
            remove_after="99.99.99",
            owner="example.owner@checkmk.com",
        ),
    ]


def test_release_field_records_metadata() -> None:
    field_info = _ExampleFlags.model_fields["example_flag"]
    extra = field_info.json_schema_extra
    assert isinstance(extra, dict)
    assert field_info.annotation is bool
    for key in _REQUIRED_METADATA:
        assert extra[key]


def test_no_expired_flags() -> None:
    current = Version.from_str(__version__)
    for name, field_info in ReleaseFlagConfig.model_fields.items():
        extra = field_info.json_schema_extra or {}
        assert isinstance(extra, dict)
        remove_after = str(extra.get("remove_after", ""))
        assert Version.from_str(remove_after) > current, (
            f"Release flag '{name}' passed its removal deadline {remove_after} "
            f"(current version {__version__}). Make the feature permanent by "
            "deleting the flag, or delete the gated code."
        )


def test_load_returns_config_when_file_missing(tmp_path: Path) -> None:
    assert isinstance(load_release_flags(tmp_path), ReleaseFlagConfig)


def test_load_ignores_unknown_flags(tmp_path: Path) -> None:
    (tmp_path / "release_flag.json").write_text('{"already_removed_flag": true}')
    flags = load_release_flags(tmp_path)
    assert not hasattr(flags, "already_removed_flag")
