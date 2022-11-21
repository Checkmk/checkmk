#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When it grows up, this file wants to provide an abstraction of the internal MKP structure"""
from __future__ import annotations

import ast
import pprint
import tarfile
from io import BytesIO
from logging import Logger
from pathlib import Path

from pydantic import BaseModel, Field

from cmk.utils import version as cmk_version

from ._type_defs import PackageException, PackageID, PackageName, PackageVersion


class PackageInfo(BaseModel):
    title: str
    name: PackageName
    description: str
    version: PackageVersion
    version_packaged: str = Field(alias="version.packaged")
    version_min_required: str = Field(alias="version.min_required")
    version_usable_until: str | None = Field(None, alias="version.usable_until")
    author: str
    download_url: str
    files: dict[str, list[str]]

    class Config:
        allow_population_by_field_name = True

    def file_content(self) -> str:
        return f"{pprint.pformat(self.dict(by_alias=True))}\n"

    def json_file_content(self) -> str:
        return self.json(by_alias=True)

    @classmethod
    def parse_python_string(cls, raw: str) -> PackageInfo:
        return cls.parse_obj(ast.literal_eval(raw))

    @property
    def id(self) -> PackageID:
        return PackageID(name=self.name, version=self.version)


def package_info_template(pacname: PackageName) -> PackageInfo:
    return PackageInfo(
        title=f"Title of {pacname}",
        name=pacname,
        description="Please add a description here",
        version=PackageVersion("1.0"),
        version_packaged=cmk_version.__version__,
        version_min_required=cmk_version.__version__,
        version_usable_until=None,
        author="Add your name here",
        download_url=f"https://example.com/{pacname}/",
        files={},
    )


def read_package_info_optionally(pkg_info_path: Path, logger: Logger) -> PackageInfo | None:
    try:
        return PackageInfo.parse_python_string(pkg_info_path.read_text())
    except Exception:
        logger.error("[%s]: Failed to read package info", pkg_info_path, exc_info=True)
    return None


def extract_package_info(file_content: bytes) -> PackageInfo:
    with tarfile.open(fileobj=BytesIO(file_content), mode="r:gz") as tar:
        try:
            if (extracted_file := tar.extractfile("info")) is None:
                raise PackageException("'info' is not a regular file")
            raw_info = extracted_file.read()
        except KeyError:
            raise PackageException("'info' not contained in MKP")
    return PackageInfo.parse_python_string(raw_info.decode())


def extract_package_info_optionally(pkg_path: Path, logger: Logger) -> PackageInfo | None:
    try:
        return extract_package_info(pkg_path.read_bytes())
    except Exception:
        # Do not make broken files / packages fail the whole mechanism
        logger.error("[%s]: Failed to read package info", pkg_path, exc_info=True)
    return None
