#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When it grows up, this file wants to provide an abstraction of the internal MKP structure"""
from __future__ import annotations

import ast
import enum
import logging
import pprint
import subprocess
import tarfile
import time
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from io import BytesIO
from logging import Logger
from pathlib import Path

from pydantic import BaseModel, Extra, Field

from cmk.utils import version as cmk_version

from ._type_defs import PackageException, PackageID, PackageName, PackageVersion


@enum.unique
class PackagePart(str, enum.Enum):
    # We have to inherit str to make the (de)serialization work as expected.
    # It's a shame, but other approaches don't work or are worse.
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

    class Config:
        allow_population_by_field_name = True
        allow_mutation = False
        extra = Extra.allow  # we used to have 'num_files' :-(

    def file_content(self) -> str:
        raw = {
            **self.dict(by_alias=True),
            "files": {p.ident: [str(f) for f in files] for p, files in self.files.items()},
        }
        return f"{pprint.pformat(raw)}\n"

    def json_file_content(self) -> str:
        return self.json(by_alias=True)

    @classmethod
    def parse_python_string(cls, raw: str) -> Manifest:
        return cls.parse_obj(ast.literal_eval(raw))

    @property
    def id(self) -> PackageID:
        return PackageID(name=self.name, version=self.version)


def manifest_template(
    name: PackageName,
    *,
    version: PackageVersion | None = None,
    files: Mapping[PackagePart, Sequence[Path]] | None = None,
) -> Manifest:
    return Manifest(
        title=f"Title of {name}",
        name=name,
        description="Please add a description here",
        version=version or PackageVersion("1.0.0"),
        version_packaged=cmk_version.__version__,
        version_min_required=cmk_version.__version__,
        version_usable_until=None,
        author="Add your name here",
        download_url=f"https://example.com/{name}/",
        files=files or {},
    )


def read_manifest_optionally(manifest_path: Path, logger: Logger | None) -> Manifest | None:
    try:
        return Manifest.parse_python_string(manifest_path.read_text())
    except Exception:
        if logger is not None:
            logger.error("[%s]: Failed to read package manifest", manifest_path, exc_info=True)
    return None


def extract_manifest(file_content: bytes) -> Manifest:
    with tarfile.open(fileobj=BytesIO(file_content), mode="r:gz") as tar:
        try:
            if (extracted_file := tar.extractfile("info")) is None:
                raise PackageException("'info' is not a regular file")
            raw_info = extracted_file.read()
        except KeyError:
            raise PackageException("'info' not contained in MKP")
    return Manifest.parse_python_string(raw_info.decode())


def extract_manifests(paths: Iterable[Path], logger: Logger) -> list[Manifest]:
    return [
        manifest
        for pkg_path in paths
        if (manifest := extract_manifest_optionally(pkg_path, logger)) is not None
    ]


def extract_manifest_optionally(pkg_path: Path, logger: Logger) -> Manifest | None:
    try:
        return _extract_manifest_cached(pkg_path, pkg_path.stat().st_mtime)
    except Exception:
        # Do not make broken files / packages fail the whole mechanism
        logger.error("[%s]: Failed to read package mainfest", pkg_path, exc_info=True)
    return None


@lru_cache
def _extract_manifest_cached(package_path: Path, mtime: float) -> Manifest:
    return extract_manifest(package_path.read_bytes())


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


def create_tgz(files: Iterable[tuple[str, bytes]]) -> bytes:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files:
            tar.addfile(_create_tar_info(name, len(content)), BytesIO(content))

    return buffer.getvalue()


def create_tar(
    name: str, src: Path, filenames: Iterable[Path], logger: logging.Logger
) -> tuple[str, bytes]:
    tarname = f"{name}.tar"
    logger.debug("  Packing %s:", tarname)
    for f in filenames:
        logger.debug("    %s", f)
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
