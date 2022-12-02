#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from tests.composition.utils import (
    agent_controller_daemon,
    bake_agent,
    clean_agent_controller,
    execute,
    get_cre_agent_path,
    install_agent_package,
)

from cmk.utils.version import Edition

site_number = 0


@pytest.fixture(name="version", scope="session")
def _version() -> CMKVersion:
    return version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_branch_name(),
    )


# Disable this. We have a site_factory instead.
@pytest.fixture(name="site", scope="module")
def _site(request):
    pass


# The scope of the site factory is "module" to avoid that changing the site properties in a module
# may result in a test failing in another one
@pytest.fixture(name="site_factory", scope="module")
def _site_factory(version: CMKVersion) -> Iterator[SiteFactory]:
    # Using a different site for every module to avoid having issues when saving the results for the
    # tests: if you call SiteFactory.save_results() twice with the same site_id, it will crash
    # because the results are already there.
    global site_number
    sf = SiteFactory(
        version=version,
        prefix=f"comp_{site_number}_",
    )
    site_number += 1
    try:
        yield sf
    finally:
        sf.save_results()
        sf.cleanup()


@pytest.fixture(name="central_site", scope="module")
def _central_site(site_factory: SiteFactory) -> Site:
    return _create_site_and_restart_httpd(site_factory, "central")


def _create_site_and_restart_httpd(site_factory: SiteFactory, site_name: str) -> Site:
    """On RHEL-based distros, such as CentOS and AlmaLinux, we have to manually restart httpd after
    creating a new site. Otherwise, the site's REST API won't be reachable via port 80, preventing
    eg. the controller from querying the agent receiver port.
    Note: the mere presence of httpd is not enough to determine whether we have to restart or not,
    see eg. sles-15sp4.
    """
    site = site_factory.get_site(site_name)
    if os.environ["DISTRO"] in {"centos-7", "centos-8", "almalinux-9"}:
        execute(["sudo", "httpd", "-k", "restart"])
    return site


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="module")
def _installed_agent_ctl_in_unknown_state(central_site: Site) -> Path:
    return install_agent_package(_agent_package_path(central_site))


def _agent_package_path(site: Site) -> Path:
    if site.version.is_raw_edition():
        return get_cre_agent_path(site)
    return bake_agent(site)[1]


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state
