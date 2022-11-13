#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When it grows up, this file wants to provide an abstraction of the internal MKP structure"""
import ast
import pprint
import tarfile
from typing import BinaryIO, TypedDict

from cmk.utils import version as cmk_version

# Would like to use class declaration here, but that is not compatible with the dots in the keys
# below.
PackageInfo = TypedDict(
    "PackageInfo",
    {
        "title": str,
        "name": str,
        "description": str,
        "version": str,
        "version.packaged": str,
        "version.min_required": str,
        "version.usable_until": str | None,
        "author": str,
        "download_url": str,
        "files": dict[str, list[str]],
    },
    total=False,
)


def get_initial_package_info(pacname: str) -> PackageInfo:
    return {
        "title": "Title of %s" % pacname,
        "name": pacname,
        "description": "Please add a description here",
        "version": "1.0",
        "version.packaged": cmk_version.__version__,
        "version.min_required": cmk_version.__version__,
        "version.usable_until": None,
        "author": "Add your name here",
        "download_url": "http://example.com/%s/" % pacname,
        "files": {},
    }


def get_optional_package_info(file_object: BinaryIO) -> PackageInfo | None:
    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        try:
            if (extracted_file := tar.extractfile("info")) is None:
                return None
            raw_info = extracted_file.read()
        except KeyError:
            return None
    return parse_package_info(raw_info.decode())


def serialize_package_info(package_info: PackageInfo) -> str:
    return pprint.pformat(package_info) + "\n"


def parse_package_info(python_string: str) -> PackageInfo:
    package_info = ast.literal_eval(python_string)
    package_info.setdefault("version.usable_until", None)
    return package_info
