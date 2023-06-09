#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import json
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Self

import pytest
import requests

from tests.testlib.site import Site


class _ExtensionName(str):
    ...


_EXPECTED_BASE_IMPORT_ERRORS: Mapping[_ExtensionName, frozenset[str]] = {}
_EXPECTED_GUI_IMPORT_ERRORS: Mapping[_ExtensionName, frozenset[str]] = {
    _ExtensionName("MSTeams"): frozenset(
        {
            "wato/msteams: name 'socket' is not defined",
        }
    ),
    _ExtensionName("cve_2021_44228_log4j"): frozenset(
        {
            "views/inv_cve_2021_22448_log4j: No module named 'cmk.gui.plugins.views.inventory'",
        }
    ),
}


@pytest.mark.parametrize(
    "extension_download_url",
    (Path(__file__).resolve().parent / "current_extensions_under_test.txt")
    .read_text()
    .strip()
    .splitlines(),
)
def test_extension_compatibility(
    site: Site,
    extension_download_url: str,
) -> None:
    site.write_binary_file(
        extension_filename := "tmp.mkp",
        _download_extension(extension_download_url),
    )
    with _install_extension(site, site.resolve_path(Path(extension_filename))) as extension_name:
        import_errors = _ImportErrors.collect_from_site(site)
        errors_human_readable = [
            *_errors_human_readable(
                component_name="base",
                encountered_import_errors=frozenset(import_errors.base_errors),
                expected_import_errors=_EXPECTED_BASE_IMPORT_ERRORS.get(
                    extension_name,
                    frozenset(),
                ),
            ),
            *_errors_human_readable(
                component_name="gui",
                encountered_import_errors=frozenset(import_errors.gui_errors),
                expected_import_errors=_EXPECTED_GUI_IMPORT_ERRORS.get(
                    extension_name,
                    frozenset(),
                ),
            ),
        ]
        assert not errors_human_readable, "Extension %s encountered the following issues:\n%s" % (
            extension_name,
            "\n".join(
                errors_human_readable,
            ),
        )


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
    try:
        name = _add_extension(site, path)
        _enable_extension(site, name)
        yield name
    finally:
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


@dataclasses.dataclass(frozen=True)
class _ImportErrors:
    base_errors: Sequence[str]
    gui_errors: Sequence[str]

    @classmethod
    def collect_from_site(cls, site: Site) -> Self:
        return cls(
            base_errors=json.loads(
                site.python_helper("_helper_failed_base_plugins.py").check_output()
            ),
            gui_errors=json.loads(
                site.python_helper("_helper_failed_gui_plugins.py").check_output()
            ),
        )


def _errors_human_readable(
    *,
    component_name: str,
    encountered_import_errors: frozenset[str],
    expected_import_errors: frozenset[str],
) -> Iterator[str]:
    if encountered_but_not_expected_errors := encountered_import_errors - expected_import_errors:
        yield "Unexpectedly encountered import errors in %s:\n%s" % (
            component_name,
            "\n".join(encountered_but_not_expected_errors),
        )
    if expected_but_not_encountered_errors := expected_import_errors - encountered_import_errors:
        yield "Expected but unencountered import errors in %s:\n%s" % (
            component_name,
            "\n".join(expected_but_not_encountered_errors),
        )
