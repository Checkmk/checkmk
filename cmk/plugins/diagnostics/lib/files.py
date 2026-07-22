#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Enumeration, sensitivity classification and collection of site files"""

import os
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import cmk.livestatus_client as livestatus
from cmk.ccc import store
from cmk.diagnostics.internal import (
    CollectContext,
    DumpItem,
    GeneratedContent,
    redact_passwords_in_content,
    REDACT_STRING,
    Sensitivity,
    VerbatimCopy,
)
from cmk.plugins.diagnostics.lib._classification import (
    CheckmkFileSensitivity,
    FileMapConfig,
    get_checkmk_file_info,
)

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


_SITES_MK = Path("multisite.d/sites.mk")


def _sanitized_sites_mk(source: Path) -> bytes:
    sites = {
        site_id: livestatus.sanitize_site_configuration(config)
        for site_id, config in store.load_from_mk_file(
            source,
            key="sites",
            default=livestatus.SiteConfigurations({}),
            lock=False,
        ).items()
    }
    with tempfile.TemporaryDirectory() as tmp:
        sanitized = Path(tmp) / "sites.mk"
        store.save_to_mk_file(sanitized, key="sites", value=sites)
        return sanitized.read_bytes()


def collect_generated_text(
    context: CollectContext, arcname: PurePosixPath, content: str, rel_filepath: Path
) -> DumpItem:
    """Redact passwords in generated text content and yield it into the dump"""
    redacted = redact_passwords_in_content(content, rel_filepath)
    if passwords_redacted := redacted.count(REDACT_STRING):
        message = f"Redacted {passwords_redacted} passwords in file {rel_filepath}"
        context.log.info(message)
    return DumpItem(arcname, GeneratedContent(redacted.encode()))


def collect_file(
    context: CollectContext, arcname: PurePosixPath, source: Path, rel_filepath: Path
) -> DumpItem:
    """Collect one site file: sanitized (sites.mk), redacted (text) or verbatim (binary)"""
    if rel_filepath == _SITES_MK:
        return DumpItem(arcname, GeneratedContent(_sanitized_sites_mk(source)))
    try:
        content = source.read_text()
    except UnicodeDecodeError:
        # We won't redact non-text files
        return DumpItem(arcname, VerbatimCopy(source))
    return collect_generated_text(context, arcname, content, rel_filepath)


def collect_bucket(
    context: CollectContext, *, file_map: FileMapConfig, bucket: Sensitivity
) -> Iterable[DumpItem]:
    """Collect all files of one category that are classified with the given sensitivity"""
    for classified in classified_files(context.omd_root, file_map):
        if classified.sensitivity is bucket:
            yield collect_file(
                context, classified.arcname, classified.source, classified.rel_filepath
            )
