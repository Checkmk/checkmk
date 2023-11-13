#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from itertools import islice
from pathlib import Path

import requests
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from cmk.utils.version import __version__, parse_check_mk_version

NUMBER_OF_EXTENSION_TESTED = 11


def main(parsed_version: int) -> None:
    most_popular = islice(
        _compatible_extensions_sorted_by_n_downloads(parsed_version), NUMBER_OF_EXTENSION_TESTED
    )
    # do not output them sorted by downloads -- this breaks the test more often than necessary.
    for extension in sorted(most_popular, key=lambda e: e.latest_version.link):
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
    all_packages_response = _ExchangeResponseAllPackages.model_validate(response.json())
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
    main(parse_check_mk_version(__version__))
