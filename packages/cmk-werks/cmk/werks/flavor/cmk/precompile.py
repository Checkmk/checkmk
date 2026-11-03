#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

from pydantic import RootModel, TypeAdapter

from cmk.ccc.version import Version
from cmk.werks.tool.flavor import current_version

from . import CmkFlavor, load_werk
from .models import EditionV2, EditionV3, WerkV1, WerkV2, WerkV3
from .translator import resolve_version

EDITION_FILTERS = [edition.value for edition in [*EditionV2, *EditionV3]]

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


def _get_filter(filter_by_edition: str | None) -> EditionV3 | None:
    if filter_by_edition is None:
        return None
    if filter_by_edition in {edition.value for edition in EditionV2}:
        return EditionV3.from_v2(EditionV2(filter_by_edition))
    return EditionV3(filter_by_edition)


def precompile(werk_dir: Path, destination: Path, filter_by_edition: str | None) -> None:
    """Writes the werks of the current major version to the destination"""
    werks_list = load_raw_files(werk_dir)

    version = current_version(CmkFlavor(), werk_dir.parent)

    edition_filter = _get_filter(filter_by_edition)

    base_version = Version.from_str(version).base

    def _set_version(werk: WerkV3) -> WerkV3:
        if werk.version is None:
            return werk.model_copy(update={"version": version})
        return werk

    def _filter(werk: WerkV3) -> bool:
        edition = werk.edition

        # include only werks matching the edition filter (if any) and this major version
        return (edition_filter is None or edition == edition_filter) and (
            Version.from_str(resolve_version(version, werk.version)).base == base_version
        )

    werks = {werk.id: _set_version(werk) for werk in werks_list if _filter(werk)}

    write_precompiled_werks(destination, werks)
