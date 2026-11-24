#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict

from cmk.flags import (
    CONFIG_FILENAME,
    experimental_field,
    ExperimentalFlagConfig,
    load_experimental_flags,
)

_REQUIRED_METADATA = ("description", "remove_ticket")


class _ExampleFlags(BaseModel):
    """Stand-in with a real flag, since ``ExperimentalFlagConfig`` may declare none."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    example_flag: Annotated[
        bool,
        experimental_field(
            description="An example flag.",
            remove_ticket="CMK-00000",
        ),
    ]


def test_experimental_field_records_metadata() -> None:
    field_info = _ExampleFlags.model_fields["example_flag"]
    extra = field_info.json_schema_extra
    assert isinstance(extra, dict)
    assert field_info.annotation is bool
    for key in _REQUIRED_METADATA:
        assert extra[key]


def test_load_returns_config_when_file_missing(tmp_path: Path) -> None:
    assert load_experimental_flags(tmp_path) == ExperimentalFlagConfig()


def test_load_returns_config_when_file_is_malformed(tmp_path: Path) -> None:
    (tmp_path / CONFIG_FILENAME).write_text("lol wrong")
    assert load_experimental_flags(tmp_path) == ExperimentalFlagConfig()


def test_load_ignores_unknown_flags(tmp_path: Path) -> None:
    (tmp_path / "release_flag.json").write_text('{"already_removed_flag": true}')
    flags = load_experimental_flags(tmp_path)
    assert not hasattr(flags, "already_removed_flag")
