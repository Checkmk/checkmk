#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This file provides an abstraction of the internal MKP structure"""

from __future__ import annotations

import ast
import enum
import logging
import pprint
import subprocess
import tarfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ._type_defs import PackageError, PackageID, PackageName, PackageVersion

_logger = logging.getLogger(__name__)


@enum.unique
class PackagePart(str, enum.Enum):
    # We have to inherit str to make the (de)serialization work as expected.
    # It's a shame, but other approaches don't work or are worse.
    CMK_PLUGINS = "cmk_plugins"
    CMK_ADDONS_PLUGINS = "cmk_addons_plugins"
    EC_RULE_PACKS = "ec_rule_packs"
    AGENT_BASED = "agent_based"
    CHECKS = "checks"
    HASI = "inventory"
    CHECKMAN = "checkman"
    AGENTS = "agents"
    NOTIFICATIONS = "notifications"
    GUI = "gui"
    WEB = "web"
    PNP_TEMPLATES = "pnp-templates"
    DOC = "doc"
    LOCALES = "locales"
    BIN = "bin"
    LIB = "lib"
    MIBS = "mibs"
    ALERT_HANDLERS = "alert_handlers"

    @property
    def ident(self) -> str:
        return self.value


class Manifest(BaseModel):
    title: str
    name: PackageName
    description: str
    version: PackageVersion
    version_packaged: str = Field(alias="version.packaged")
    version_min_required: str = Field(alias="version.min_required")
    version_usable_until: str | None = Field(None, alias="version.usable_until")
    author: str
    download_url: str
    files: Mapping[PackagePart, Sequence[Path]]

    model_config = ConfigDict(
        populate_by_name=True,
        frozen=True,
        extra="allow",  # we used to have 'num_files' :-(
    )

    def file_content(self) -> str:
        raw = {
            **self.model_dump(by_alias=True),
            "files": {p.ident: [str(f) for f in files] for p, files in self.files.items()},
        }
        return f"{pprint.pformat(raw)}\n"

    def json_file_content(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def parse_python_string(cls, raw: str) -> Manifest:
        return cls.model_validate(ast.literal_eval(raw))

    @property
    def id(self) -> PackageID:
        return PackageID(name=self.name, version=self.version)


def manifest_template(
    name: PackageName,
    version_packaged: str,
    version_required: str,
    *,
    version: PackageVersion | None = None,
    files: Mapping[PackagePart, Sequence[Path]] | None = None,
) -> Manifest:
    return Manifest(
        title=f"Title of {name}",
        name=name,
        description="Please add a description here",
        version=version or PackageVersion("1.0.0"),
        version_packaged=version_packaged,
        version_min_required=version_required,
        version_usable_until=None,
        author="Add your name here",
        download_url=f"https://example.com/{name}/",
        files=files or {},
    )


def read_manifest_optionally(manifest_path: Path) -> Manifest | None:
    try:
        return Manifest.parse_python_string(manifest_path.read_text())
    except (OSError, SyntaxError, TypeError, ValueError, ValidationError):
        _logger.error("[%s]: Failed to read package manifest", manifest_path, exc_info=True)
    return None


def extract_manifest(file_content: bytes) -> Manifest:
    with tarfile.open(fileobj=BytesIO(file_content), mode="r:gz") as tar:
        try:
            if (extracted_file := tar.extractfile("info")) is None:
                raise PackageError("'info' is not a regular file")
            raw_info = extracted_file.read()
        except KeyError as exc:
            raise PackageError("'info' not contained in MKP") from exc
    return Manifest.parse_python_string(raw_info.decode())


def extract_manifests(paths: Iterable[Path]) -> list[Manifest]:
    return [
        manifest
        for pkg_path in paths
        if (manifest := extract_manifest_optionally(pkg_path)) is not None
    ]


def extract_manifest_optionally(pkg_path: Path) -> Manifest | None:
    try:
        return _extract_manifest_cached(pkg_path, pkg_path.stat().st_mtime)
    except Exception:
        # Do not make broken files / packages fail the whole mechanism
        _logger.error("[%s]: Failed to read package mainfest", pkg_path, exc_info=True)
    return None


@lru_cache
def _extract_manifest_cached(package_path: Path, _mtime: float) -> Manifest:
    return extract_manifest(package_path.read_bytes())


def create_mkp(
    manifest: Manifest,
    site_paths: Callable[[PackagePart], Path],
    version_packaged: str,
) -> bytes:
    manifest = Manifest(
        title=manifest.title,
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        version_packaged=version_packaged,
        version_min_required=manifest.version_min_required,
        version_usable_until=manifest.version_usable_until,
        author=manifest.author,
        download_url=manifest.download_url,
        files=manifest.files,
    )

    return _create_tgz(
        (
            # add the regular info file (Python format)
            ("info", manifest.file_content().encode()),
            # add the info file a second time (JSON format) for external tools
            ("info.json", manifest.json_file_content().encode()),
            # Now pack the actual files into sub tars
            *(
                _create_tar(part.ident, site_paths(part), filenames)
                for part, filenames in manifest.files.items()
                if filenames
            ),
        )
    )


def _create_tar_info(filename: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo()
    info.mtime = int(time.time())
    info.uid = 0
    info.gid = 0
    info.size = size
    info.mode = 0o644
    info.type = tarfile.REGTYPE
    info.name = filename
    return info


def _create_tgz(files: Iterable[tuple[str, bytes]]) -> bytes:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files:
            tar.addfile(_create_tar_info(name, len(content)), BytesIO(content))

    return buffer.getvalue()


def _create_tar(name: str, src: Path, filenames: Iterable[Path]) -> tuple[str, bytes]:
    tarname = f"{name}.tar"
    _logger.debug("  Packing %s:", tarname)
    for f in filenames:
        _logger.debug("    %s", f)
    return tarname, subprocess.check_output(
        [
            "tar",
            "cf",
            "-",
            "--dereference",
            "--force-local",
            "-C",
            str(src),
            *(str(f) for f in filenames),
        ]
    )


def extract_mkp(
    manifest: Manifest,
    mkp: bytes,
    site_paths: Callable[[PackagePart], Path],
) -> None:
    _extract_tgz(
        mkp,
        [
            (f"{part.ident}.tar", site_paths(part), filenames)
            for part, filenames in manifest.files.items()
            if filenames
        ],
    )


def _extract_tgz(mkp: bytes, content: Iterable[tuple[str, Path, Iterable[Path]]]) -> None:
    with tarfile.open(fileobj=BytesIO(mkp), mode="r:gz") as tar:
        for tarname, dst, filenames in content:
            _extract_tar(tar, tarname, dst, filenames)


def _extract_tar(tar: tarfile.TarFile, name: str, dst: Path, filenames: Iterable[Path]) -> None:
    _logger.debug("  Extracting '%s':", name)
    for fn in filenames:
        _logger.debug("    %s", fn)

    if not dst.exists():
        # make sure target directory exists
        _logger.debug("    Creating directory %s", dst)
        dst.mkdir(parents=True, exist_ok=True)

    tarsource = tar.extractfile(name)
    if tarsource is None:
        raise PackageError(f"Failed to open {name}")

    # Important: Do not preserve the tared timestamp.
    # Checkmk needs to know when the files have been installed for cache invalidation.
    with subprocess.Popen(
        ["tar", "xf", "-", "--touch", "-C", str(dst), *(str(f) for f in filenames)],
        stdin=subprocess.PIPE,
        shell=False,
        close_fds=True,
    ) as tardest:
        if tardest.stdin is None:
            raise PackageError("Failed to open stdin")

        while True:
            data = tarsource.read(4096)
            if not data:
                break
            tardest.stdin.write(data)
