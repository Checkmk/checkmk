#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest
import requests
from pydantic import BaseModel

from tests.testlib.site import Site

from cmk.ccc.version import parse_check_mk_version


def download_extension(url: str, timeout: int = 10) -> bytes:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.ConnectionError as e:
        raise pytest.skip(f"Encountered connection issues when attempting to download {url}") from e
    if not response.ok:
        raise pytest.skip(
            f"Got non-200 response when downloading {url}: {response.status_code}. "
            f"Raw response: {response.text}"
        )
    try:
        # if the response is valid json, something went wrong (we still get HTTP 200 though ...)
        raise pytest.skip(f"Downloading {url} failed: {response.json()}")
    except ValueError:
        return response.content
    return response.content


class DownloadedExtension(NamedTuple):
    name: str
    version: str


@contextlib.contextmanager
def install_extensions(site: Site, paths: list[Path]) -> Iterator[list[DownloadedExtension]]:
    added_extensions = []
    try:
        for path in paths:
            extension = add_extension(site, path)
            enable_extension(site, extension.name, extension.version)
            added_extensions.append(extension)
        yield added_extensions
    finally:
        for extension in added_extensions:
            disable_extension(site, extension.name, extension.version)
            remove_extension(site, extension.name, extension.version)


def add_extension(site: Site, path: Path) -> DownloadedExtension:
    command_output = site.check_output(["mkp", "add", str(path)])
    name, version = command_output.splitlines()[0].split(maxsplit=1)
    return DownloadedExtension(name, version)


def enable_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "enable", name, version])


def disable_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "disable", name, version])


def remove_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "remove", name, version])


def compatible_extensions_sorted_by_n_downloads(parsed_version: int) -> list[Extension]:
    return sorted(
        compatible_extensions(parsed_version),
        key=lambda extension: extension.downloads,
        reverse=True,
    )


def compatible_extensions(parsed_version: int, timeout: int = 10) -> Iterator[Extension]:
    response = requests.get("https://exchange.checkmk.com/api/packages/all", timeout=timeout)
    response.raise_for_status()
    all_packages_response = ExchangeResponseAllPackages.model_validate(response.json())
    assert all_packages_response.success, "Querying packages from Checkmk exchange unsuccessful"
    for extension in all_packages_response.data.packages:
        try:
            min_version = parse_check_mk_version(extension.latest_version.min_version)
        except ValueError:
            continue
        if min_version < parsed_version:
            yield extension


class LatestVersion(BaseModel):
    id: int
    min_version: str
    link: str


class Extension(BaseModel):
    id: int
    latest_version: LatestVersion
    downloads: int


class ExchangeResponseAllPackagesData(BaseModel):
    packages: Sequence[Extension]


class ExchangeResponseAllPackages(BaseModel):
    success: bool
    data: ExchangeResponseAllPackagesData
