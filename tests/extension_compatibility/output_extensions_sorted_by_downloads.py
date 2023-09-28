#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

import requests
from pydantic import BaseModel


def main(parsed_version: int) -> None:
    for extension in _compatible_extensions_sorted_by_n_downloads(parsed_version):
        print(extension.latest_version.link)


def _compatible_extensions_sorted_by_n_downloads(parsed_version: int) -> list[_Extension]:
    return sorted(
        _compatible_extensions(parsed_version),
        key=lambda extension: extension.downloads,
        reverse=True,
    )


def _compatible_extensions(parsed_version: int) -> Iterator[_Extension]:
    response = requests.get("https://exchange.checkmk.com/api/packages/all")
    response.raise_for_status()
    all_packages_response = _ExchangeResponseAllPackages.parse_obj(response.json())
    assert all_packages_response.success, "Querying packages from Checkmk exchange unsuccessful"
    for extension in all_packages_response.data.packages:
        try:
            min_version = parse_check_mk_version(extension.latest_version.min_version)
        except ValueError:
            continue
        if min_version < parsed_version:
            yield extension


class _LatestVersion(BaseModel, frozen=True):
    id: int
    min_version: str
    link: str


class _Extension(BaseModel, frozen=True):
    id: int
    latest_version: _LatestVersion
    downloads: int


class _ExchangeResponseAllPackagesData(BaseModel, frozen=True):
    packages: Sequence[_Extension]


class _ExchangeResponseAllPackages(BaseModel, frozen=True):
    success: bool
    data: _ExchangeResponseAllPackagesData


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from cmk.utils.version import __version__, parse_check_mk_version

    main(parse_check_mk_version(__version__))
