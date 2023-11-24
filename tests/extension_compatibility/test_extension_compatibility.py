#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Self

import pytest
import requests

from tests.testlib.site import Site


class _ExtensionName(str):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class _ImportErrors:
    base_errors: set[str] = dataclasses.field(default_factory=set)
    gui_errors: set[str] = dataclasses.field(default_factory=set)

    @classmethod
    def collect_from_site(cls, site: Site) -> Self:
        return cls(
            base_errors=set(
                json.loads(site.python_helper("_helper_failed_base_plugins.py").check_output())
            ),
            gui_errors=set(
                json.loads(site.python_helper("_helper_failed_gui_plugins.py").check_output())
            ),
        )


_DOWNLOAD_URL_BASE = "https://exchange.checkmk.com/api/packages/download/"


_EXPECTED_IMPORT_ERRORS: Mapping[str, _ImportErrors] = {
    "MSTeams-2.1.mkp": _ImportErrors(
        gui_errors={
            "wato/msteams: name 'socket' is not defined",
        }
    ),
    "apcaccess-5.2.2.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin apcaccess: cannot import name 'temperature' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
        }
    ),
    "kentix_devices-3.0.1.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin kentix_devices: No module named 'cmk.base.plugins.agent_based.utils.temperature'\n",
        }
    ),
    "ceph-11.17.2.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin cephosd: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephosdbluefs: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephstatus: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephdf: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
        }
    ),
}


def _get_tested_extensions() -> Iterable[tuple[str, str]]:
    return [
        (url, url.rsplit("/", 1)[-1])
        for url in (Path(__file__).resolve().parent / "current_extensions_under_test.txt")
        .read_text()
        .strip()
        .splitlines()
    ]


@pytest.mark.parametrize(
    "extension_download_url, name",
    [pytest.param(url, name, id=name) for url, name in _get_tested_extensions()],
)
def test_extension_compatibility(
    site: Site,
    extension_download_url: str,
    name: str,
) -> None:
    site.write_binary_file(
        extension_filename := "tmp.mkp",
        _download_extension(extension_download_url),
    )
    with _install_extension(site, site.resolve_path(Path(extension_filename))):
        encountered_errors = _ImportErrors.collect_from_site(site)
        expected_errors = _EXPECTED_IMPORT_ERRORS.get(name, _ImportErrors())

    assert encountered_errors.base_errors == expected_errors.base_errors
    assert encountered_errors.gui_errors == expected_errors.gui_errors


def _download_extension(url: str) -> bytes:
    try:
        response = requests.get(url)
    except requests.ConnectionError as e:
        raise pytest.skip(f"Encountered connection issues when attempting to download {url}") from e
    if not response.ok:
        raise pytest.skip(
            f"Got non-200 response when downloading {url}: {response.status_code}. Raw response: {response.text}"
        )
    try:
        # if the response is valid json, something went wrong (we still get HTTP 200 though ...)
        raise pytest.skip(f"Downloading {url} failed: {response.json()}")
    except ValueError:
        return response.content
    return response.content


@contextlib.contextmanager
def _install_extension(site: Site, path: Path) -> Iterator[_ExtensionName]:
    name = None
    try:
        name = _add_extension(site, path)
        _enable_extension(site, name)
        yield name
    finally:
        if name:
            _disable_extension(site, name)
            _remove_extension(site, name)


def _add_extension(site: Site, path: Path) -> _ExtensionName:
    return _ExtensionName(site.check_output(["mkp", "add", str(path)]).splitlines()[0].split()[0])


def _enable_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "enable", name])


def _disable_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "disable", name])


def _remove_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "remove", name])
