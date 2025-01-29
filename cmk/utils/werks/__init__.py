#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for processing Checkmk werks. This is needed by several components,
so it's best place is in the central library.

We are currently in the progress of moving the werk files from nowiki syntax to
markdown. The files written by the developers (in `.werks` folder in this repo)
contain markdown if the filenames ends with `.md`, otherwise nowiki syntax.

In order to speed up the loading of the werk files they are precompiled and
packaged as json during release. Pydantic model Werk is used to handle the
serializing and deserializing.

But all this should be implementation details, because downstream tools should
only handle the WerkV2 model. Old style werks are converted to markdown Werks,
so both can be handled with a common interface.
"""

from pathlib import Path
from typing import Protocol, TypeVar

import cmk.utils.paths

from cmk.werks.models import Werk, WerkV1
from cmk.werks.parse import parse_werk_v1
from cmk.werks.utils import (
    load_precompiled_werks_file,
)


class GuiWerkProtocol(Protocol):
    werk: Werk
    acknowledged: bool


GWP = TypeVar("GWP", bound=GuiWerkProtocol)


def _compiled_werks_dir() -> Path:
    return Path(cmk.utils.paths.share_dir, "werks")


def load(base_dir: Path | None = None) -> dict[int, Werk]:
    if base_dir is None:
        base_dir = _compiled_werks_dir()

    werks: dict[int, Werk] = {}
    for file_name in [(base_dir / "werks"), *base_dir.glob("werks-*")]:
        werks.update(load_precompiled_werks_file(file_name))
    return werks


# THIS IS A TEMPORARY FIX FOR THE OLD WORKFLOW


def load_raw_files_old(werks_dir: Path) -> list[WerkV1]:
    if werks_dir is None:
        werks_dir = _compiled_werks_dir()
    werks: list[WerkV1] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            parsed = parse_werk_v1(file_name.read_text(), int(file_name.name))
            werk: dict[str, str | int | list[str]] = {}
            werk.update(parsed.metadata)
            werk["description"] = parsed.description
            werks.append(WerkV1.model_validate(werk))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


# TEMPORARY FIX END!
