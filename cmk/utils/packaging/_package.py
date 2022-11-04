#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When it grows up, this file wants to provide an abstraction of the internal MKP structure"""
from __future__ import annotations

import ast
import pprint
import tarfile
from typing import BinaryIO

from pydantic import BaseModel, Field

from cmk.utils import version as cmk_version


class PackageInfo(BaseModel):
    title: str
    name: str
    description: str
    version: str
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


def package_info_template(pacname: str) -> PackageInfo:
    return PackageInfo(
        title=f"Title of {pacname}",
        name=pacname,
        description="Please add a description here",
        version="1.0",
        version_packaged=cmk_version.__version__,
        version_min_required=cmk_version.__version__,
        version_usable_until=None,
        author="Add your name here",
        download_url=f"https://example.com/{pacname}/",
        files={},
    )


def get_optional_package_info(file_object: BinaryIO) -> PackageInfo | None:
    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        try:
            if (extracted_file := tar.extractfile("info")) is None:
                return None
            raw_info = extracted_file.read()
        except KeyError:
            return None
    return PackageInfo.parse_python_string(raw_info.decode())
