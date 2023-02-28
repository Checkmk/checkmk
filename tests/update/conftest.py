#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import logging

import pytest

from tests.testlib.site import CMKVersion, Edition, Site, SiteFactory
from tests.testlib.utils import current_base_branch_name

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseVersions:
    BASE_VERSIONS = [
        CMKVersion("2.1.0p1", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p11", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p22", Edition.CEE, current_base_branch_name()),
    ]
    IDS = [f"from_{base_version.version_directory()}_to_daily" for base_version in BASE_VERSIONS]


def _get_site(version: CMKVersion, update: bool) -> Site:
    """Install or update the test site with the given version."""

    sf = SiteFactory(
        version=CMKVersion(version.version, version.edition, current_base_branch_name()),
        prefix="update_",
        update_from_git=False,
        install_test_python_modules=False,
        update=update,
        enforce_english_gui=False,
    )
    site = sf.get_existing_site("central")

    logger.info("Site exists: %s", site.exists())
    if site.exists():
        if not update:
            logger.info("Dropping existing site ...")
            site.rm()
        elif site.is_running():
            logger.info("Stopping running site before update ...")
            site.stop()
    logger.info("Creating new site")
    site = sf.get_site("central")
    logger.info("Test-site %s is up", site.id)

    return site


@pytest.fixture(name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS)
def get_site(request: pytest.FixtureRequest) -> Site:
    """Install the test site with the base version."""
    base_version = request.param
    logger.info("Setting up test-site ...")
    return _get_site(base_version, update=False)


def update_site(target_version: CMKVersion) -> Site:
    """Update the test site to the target version."""
    return _get_site(target_version, update=True)
