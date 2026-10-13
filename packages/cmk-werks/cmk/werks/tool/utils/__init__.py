#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

from pydantic import RootModel, TypeAdapter

from cmk.werks.tool import load_werk
from cmk.werks.tool.models import WerkV1, WerkV2, WerkV3

WerksOnDisk = RootModel[dict[int, WerkV2 | WerkV3]]


def load_precompiled_werks_file(path: Path) -> dict[int, WerkV3]:
    # ? what is the content of these files, to which the path shows
    # There is no performance issue with this TypeAdapter call
    # astrein: disable=pydantic-type-adapter
    adapter = TypeAdapter(dict[int, WerkV3 | WerkV2 | WerkV1])
    with path.open("r", encoding="utf-8") as f:

        def generator() -> Iterator[tuple[int, WerkV3]]:
            for werk_id, werk in adapter.validate_json(f.read()).items():
                if isinstance(werk, (WerkV1, WerkV2)):
                    yield werk_id, werk.to_werk()
                else:
                    yield werk_id, werk

        return dict(generator())


def load_raw_files(werks_dir: Path) -> list[WerkV3]:
    werks: list[WerkV3] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            werks.append(load_werk(file_content=file_name.read_text(), file_name=file_name.name))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


def write_precompiled_werks(path: Path, werks: dict[int, WerkV3]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        fp.write(WerksOnDisk.model_validate(werks).model_dump_json(by_alias=True))
