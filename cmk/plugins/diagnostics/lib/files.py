#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Enumeration and sensitivity classification of collectable site files"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# TODO: The classification table and the file map configs still live in the
# transitional cmk.diagnostics package because the GUI still consumes them
# there; they move here once the GUI is migrated.
from cmk.diagnostics.engine import (
    CheckmkFileSensitivity,
    FileMapConfig,
    get_checkmk_file_info,
)
from cmk.diagnostics.internal import DumpItem, Sensitivity, VerbatimCopy

_SENSITIVITY_OF = {
    CheckmkFileSensitivity.insensitive: Sensitivity.LOW,
    CheckmkFileSensitivity.sensitive: Sensitivity.MEDIUM,
    CheckmkFileSensitivity.high_sensitive: Sensitivity.HIGH,
    # Be conservative about files nobody classified.
    CheckmkFileSensitivity.unknown: Sensitivity.HIGH,
}


@dataclass(frozen=True)
class ClassifiedFile:
    arcname: PurePosixPath
    """Path of the file inside the dump (relative to the site root)"""
    source: Path
    """Absolute path of the existing file"""
    rel_filepath: Path
    """Path relative to the category's base folder (classification key)"""
    sensitivity: Sensitivity


def walk_verbatim(root: Path, arcbase: PurePosixPath) -> Iterator[DumpItem]:
    """Yield every file below root as a verbatim copy under arcbase"""
    for path, _dirs, files in root.walk():
        for file in files:
            source = path / file
            yield DumpItem(arcbase / source.relative_to(root), VerbatimCopy(source))


def classified_files(omd_root: Path, file_map: FileMapConfig) -> Iterator[ClassifiedFile]:
    """Walk one file category and classify each file's sensitivity"""
    base_folder = omd_root / file_map.rel_base_folder
    files_map = file_map.map_generator(base_folder, lambda folder: list(os.walk(folder)))
    for rel_str, source in sorted(files_map.items()):
        yield ClassifiedFile(
            arcname=PurePosixPath(file_map.rel_base_folder) / rel_str,
            source=source,
            rel_filepath=Path(rel_str),
            sensitivity=_SENSITIVITY_OF[get_checkmk_file_info(rel_str).sensitivity],
        )
