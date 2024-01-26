#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import enum
import json
import re
from typing import Iterator

import pipfile  # type: ignore


def insert_pinned_version(p_to_v: dict[str, str], args: argparse.Namespace) -> None:
    # In order to preserve comments, we need to go the manual path
    with open(args.path_to_pipfile) as pipfile_read:
        lines = pipfile_read.readlines()

    for i, line in enumerate(lines):
        if package_match := re.match(r"(^.*) = \"*\".*", line):
            package_name = package_match.groups()[0]
            if pinned_version := p_to_v.get(package_name):
                lines[i] = line.replace('"*"', f'"{pinned_version}"')

    with open(args.path_to_pipfile, "w") as pipfile_write:
        pipfile_write.writelines(lines)


class PackageType(enum.StrEnum):
    # See also discussion in slack why we're also pinning dev-packages:
    # https://tribe29.slack.com/archives/CGBE6U2PK/p1706523946468149
    # and wiki
    # https://wiki.lan.tribe29.com/books/how-to/page/creating-a-new-beta-branch#bkmrk-pin-dev-dependencies
    default = "packages"
    develop = "dev-packages"


def find_unpinned_packages(data: dict) -> Iterator[str]:
    yield from [p for p, v in data.items() if "*" in v]


def get_version_from_pipfile_lock(package_name: str, package_type: str, pipfile_lock: dict) -> str:
    return pipfile_lock[package_type][package_name]["version"]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
        This script can be used to replace unpinned package versions with the version which is
        currently locked in a Pipfile.lock. We usally do this when branching from master
        into the next stable release in order to have reproducible builds.
        """
    )

    parser.add_argument("--path_to_pipfile", required=True)
    parser.add_argument("--path_to_pipfile_lock", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    loaded_pipfile = pipfile.Pipfile.load(args.path_to_pipfile)
    with open(args.path_to_pipfile_lock) as pl:
        loaded_pipfile_lock = json.load(pl)

    package_to_version = {}

    for p_type in PackageType:
        for package in find_unpinned_packages(loaded_pipfile.data[p_type.name]):
            version = get_version_from_pipfile_lock(
                package,
                package_type=p_type.name,
                pipfile_lock=loaded_pipfile_lock,
            )
            package_to_version[package] = version
    insert_pinned_version(package_to_version, args)
