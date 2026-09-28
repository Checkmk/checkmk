#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Which Checkmk package is under test, and what that means for the tests.

The edition, version and site lifecycle are configured via environment variables
(EDITION, VERSION, REUSE, CLEANUP), read all over tests.testlib. The options here
are a command line front door to those variables: they are written back to the
environment before any site is created.

On top of that this plugin provides the `skip_if_edition`, `skip_if_not_edition`,
`skip_if_containerized` and `skip_if_not_containerized` markers, records the
environment in the pytest-html report, reports site crashes after each test and
renders the state of the OMD sites on the host for a failure report.

Register from a conftest's `pytest_addoption` via
`tests.testlib.pytest_helpers.registration.register_pytest_plugins`.
"""

import os
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Final

import pytest
from pytest_metadata.plugin import metadata_key  # type: ignore[import-untyped,unused-ignore]

from tests.testlib.common.repo import current_base_branch_name
from tests.testlib.common.utils2 import is_containerized
from tests.testlib.common.version import CMKEdition, CMKVersion, edition_from_env, TypeCMKEdition
from tests.testlib.pytest_helpers import faked_artifacts, registration
from tests.testlib.pytest_helpers.diagnostics import render_command_output
from tests.testlib.system.site import Site

ARG_EDITION_CMK: Final[str] = "--cmk-edition"
ARG_VERSION_CMK: Final[str] = "--cmk-version"
ARG_REUSE: Final[str] = "--reuse"
ARG_NO_CLEANUP: Final[str] = "--no-cleanup"


class EditionMarker(StrEnum):
    skip_if = "skip_if_edition"
    skip_if_not = "skip_if_not_edition"


class ContainerizedMarker(StrEnum):
    skip_if = "skip_if_containerized"
    skip_if_not = "skip_if_not_containerized"


def pytest_addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:
    registration.register_pytest_plugins(
        pluginmanager, faked_artifacts
    )  # the crash report needs to know about faked artifacts
    parser.addoption(
        "--ignore-running-procs",
        action="store_true",
        default=False,
        help="Ignore running processes after site shutdown.",
    )
    parser.addoption(
        ARG_VERSION_CMK,
        action="store",
        type=str,
        metavar="2.X.0[pZ|-YYYY.MM.DD]",
        help=(
            "Select version of the Checkmk site under test. If not set, value of environment "
            "variable 'VERSION' is used, if available. If neither is set, 'daily' is used."
        ),
        default=os.getenv("VERSION", CMKVersion.DAILY),
    )
    parser.addoption(
        ARG_EDITION_CMK,
        action="store",
        choices=[
            CMKEdition.ULTIMATE.long,
            CMKEdition.PRO.long,
            CMKEdition.ULTIMATEMT.long,
            CMKEdition.COMMUNITY.long,
            CMKEdition.CLOUD.long,
        ],
        type=str,
        help=(
            "Select edition of the Checkmk site under test. If not set, value of environment "
            "variable 'EDITION' is used, if available. If neither is set, 'pro' is used."
        ),
        default=os.getenv("EDITION", CMKEdition.PRO.long),
    )
    parser.addoption(
        ARG_REUSE,
        action="store_true",
        default=False,
        help=(
            "Reuse an existing site to perform the tests. If not set, value of environment "
            "variable 'REUSE' is used, if available. If neither is set, reuse is disabled."
        ),
    )
    parser.addoption(
        ARG_NO_CLEANUP,
        action="store_true",
        default=False,
        help=(
            "Avoid cleanup the test-environment after a test-run. If not set, value of environment "
            "variable 'CLEANUP' is used, if available. If neither is set, cleanup is enabled."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Export the options to the environment, record it in the report, register the markers"""

    if config.getoption(ARG_REUSE):
        os.environ["REUSE"] = "1"

    if config.getoption(ARG_NO_CLEANUP):
        os.environ["CLEANUP"] = "0"

    os.environ["EDITION"] = config.getoption(ARG_EDITION_CMK)
    os.environ["VERSION"] = config.getoption(ARG_VERSION_CMK)

    env_vars = {
        "BRANCH": current_base_branch_name(),
        "EDITION": "pro",
        "VERSION": "daily",
        "DISTRO": "",
        "TZ": "UTC",
        "REUSE": "0",
        "CLEANUP": "1",
    }
    env_lines = [f"{key}={os.getenv(key, val)}" for key, val in env_vars.items() if val]
    config.stash[metadata_key]["Variables"] = (
        "<ul><li>\n" + ("</li><li>\n".join(env_lines)) + "</li></ul>"
    )

    config.addinivalue_line(
        "markers",
        f"{EditionMarker.skip_if}(edition): skips the tests for the given edition(s)",
    )
    config.addinivalue_line(
        "markers",
        f"{EditionMarker.skip_if_not}(edition): "
        "skips the tests for anything but the given edition(s)",
    )
    config.addinivalue_line(
        "markers",
        f"{ContainerizedMarker.skip_if}: skips the tests for containerized runs",
    )
    config.addinivalue_line(
        "markers",
        f"{ContainerizedMarker.skip_if_not}: skips the tests for uncontainerized runs",
    )


def _editions_from_markers(item: pytest.Item, marker_name: EditionMarker) -> list[TypeCMKEdition]:
    editions: list[TypeCMKEdition] = []
    for mark in item.iter_markers(name=marker_name):
        editions += [CMKEdition.edition_from_text(edition_arg) for edition_arg in mark.args]
    return editions


@pytest.hookimpl(tryfirst=True)  # skips come before the dry-run xfail of `selection`
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests for specific editions or environments"""
    current_edition = edition_from_env()

    skip_editions = _editions_from_markers(item, EditionMarker.skip_if)
    if skip_editions and current_edition in skip_editions:
        pytest.skip(f'{item.nodeid}: Edition "{current_edition.long}" is skipped explicitly!')

    unskip_editions = _editions_from_markers(item, EditionMarker.skip_if_not)
    if unskip_editions and current_edition not in unskip_editions:
        pytest.skip(f'{item.nodeid}: Edition "{current_edition.long}" is skipped implicitly!')

    skip_containerized = next(item.iter_markers(name=ContainerizedMarker.skip_if), None)
    if skip_containerized and is_containerized():
        pytest.skip(f"{item.nodeid}: Containerized run excluded!")

    skip_not_containerized = next(item.iter_markers(name=ContainerizedMarker.skip_if_not), None)
    if skip_not_containerized and not is_containerized():
        pytest.skip(f"{item.nodeid}: Containerized run required!")


@pytest.hookimpl
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Report crashes of every site the test got as a fixture."""
    ignore_bakery_crashes = faked_artifacts.package_contains_faked_artifacts(item.config)
    for obj in getattr(item, "funcargs", {}).values():
        if isinstance(obj, Site):
            obj.report_crashes(ignore_bakery_crashes=ignore_bakery_crashes)


def add_host_diagnostics(excp: BaseException, sudo: bool) -> None:
    """Attach the process list and, for every OMD site on the host, its locks and status.

    Meant for suites with several sites talking to each other, where the test alone
    rarely tells which site got stuck.
    """
    excp.add_note("-" * 80)
    excp.add_note(render_command_output("ps -ef", sudo=sudo))
    if not sudo:
        excp.add_note("-" * 80)
        excp.add_note(render_command_output("lslocks --output-all --notruncate", sudo=False))
        return
    for site_name in _omd_site_names():
        excp.add_note("-" * 80)
        excp.add_note(f"SITE: {site_name}")
        for command_output in _site_diagnostics(site_name):
            excp.add_note("-" * 80)
            excp.add_note(command_output)


def _omd_site_names() -> Iterator[str]:
    """Yield the names of all currently existing OMD sites"""
    sites = Path("/omd/sites")
    if sites.is_dir():
        yield from (site_path.name for site_path in sites.iterdir())


def _site_diagnostics(site_name: str) -> Iterator[str]:
    """Yield rendered output for OMD site command-by-command"""
    for cmd in (
        "lslocks --output-all --notruncate",
        "cmk-ui-job-scheduler-health",
        "omd status",
        'lq "GET hosts\\nColumns: name"',
    ):
        yield render_command_output(cmd, sudo=True, substitute_user=site_name)
