#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
import dataclasses
import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Self

import pytest
import requests
from pydantic import BaseModel

from tests.testlib.site import Site

from cmk.utils.version import __version__, parse_check_mk_version

NUMBER_OF_EXTENSIONS_CHECKED = 30
NUMBER_OF_EXTENSIONS_TESTED = 30


CURRENTLY_UNDER_TEST = (
    "https://exchange.checkmk.com/api/packages/download/101/dovereplstat-4.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/12/apcaccess-5.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/161/kentix_devices-3.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/170/lsbrelease-5.7.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/181/memcached-5.7.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/184/mikrotik-2.4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/209/netifaces-7.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/244/rspamd-1.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/261/sslcertificates-8.8.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/307/amavis-6.1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/309/ceph-11.17.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/319/hpsa-8.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/321/SIGNL4-2.1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/332/win_scheduled_task-2.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/36/check_mk_api-5.5.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/361/win_adsync-2.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/362/yum-2.4.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/369/veeam_o365-2.6.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/370/wireguard-1.5.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/375/robotmk.v1.4.1-cmk2.mkp",
    "https://exchange.checkmk.com/api/packages/download/379/proxmox_provisioned-1.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/418/acgateway-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/426/MSTeams-2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/427/vsan-2.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/467/check_snmp-0.5.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/468/check_snmp_metric-0.4.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/503/cve_2021_44228_log4j_cmk20.mkp",
    "https://exchange.checkmk.com/api/packages/download/510/hpe_ilo-4.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/652/redfish-2.2.19.mkp",
    "https://exchange.checkmk.com/api/packages/download/77/cpufreq-2.3.1.mkp",
)


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
    "ceph-11.17.2.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin cephosd: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephosdbluefs: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephstatus: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin cephdf: cannot import name 'df' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
        }
    ),
    "cve_2021_44228_log4j_cmk20.mkp": _ImportErrors(
        gui_errors={
            "views/inv_cve_2021_22448_log4j: No module named 'cmk.gui.plugins.views.inventory'",
        },
    ),
    "hpe_ilo-4.0.0.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin ilo_api_temp: No module named 'cmk.base.plugins.agent_based.utils.temperature'\n",
        }
    ),
    "kentix_devices-3.0.1.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin kentix_devices: No module named 'cmk.base.plugins.agent_based.utils.temperature'\n",
        }
    ),
    "redfish-2.2.19.mkp": _ImportErrors(
        base_errors={
            "Error in agent based plugin redfish_temperatures: No module named 'cmk.base.plugins.agent_based.utils.temperature'\n",
        }
    ),
    "veeam_o365-2.6.1.mkp": _ImportErrors(
        gui_errors={
            "metrics/veeam_o365jobs: cannot import name 'check_metrics' from 'cmk.gui.plugins.metrics.utils' (/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/metrics/utils.py)",
            "metrics/veeam_o365licenses: cannot import name 'check_metrics' from 'cmk.gui.plugins.metrics.utils' (/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/metrics/utils.py)",
        },
    ),
}


def _get_tested_extensions() -> Iterable[tuple[str, str]]:
    return [(url, url.rsplit("/", 1)[-1]) for url in CURRENTLY_UNDER_TEST]


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


def test_package_list_up_to_date() -> None:
    parsed_version = parse_check_mk_version(__version__)
    extensions = _compatible_extensions_sorted_by_n_downloads(parsed_version)

    # uncomment this to get output that you can paste into a spread sheet.
    # for extension in extensions:
    #     print(f"{extension.latest_version.link}\t{extension.downloads:5}")

    # the #N tested ones should be amongst the #M most popular ones.
    tested_unpopular = set(CURRENTLY_UNDER_TEST) - {
        e.latest_version.link for e in extensions[:NUMBER_OF_EXTENSIONS_CHECKED]
    }
    assert not tested_unpopular


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
