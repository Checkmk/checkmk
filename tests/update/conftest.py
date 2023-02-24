#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import logging
import os

import pytest

from tests.testlib.site import CMKVersion, Edition, Site, SiteFactory
from tests.testlib.utils import current_base_branch_name

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseVersions:
    BASE_VERSIONS = [
        "2.1.0p1",
    ]
    IDS = [f"base-version: {base_version}" for base_version in BASE_VERSIONS]


def _get_site(version: str, update: bool) -> Site:

    # we need to provide the version here for install-cmk.py
    os.environ["VERSION"] = version

    # we need to skip the enforce_non_localized_gui() call since it will fail for older releases
    os.environ["SKIP_ENFORCE_NON_LOCALIZED_GUI"] = "1"

    sf = SiteFactory(
        version=CMKVersion(version, Edition.CEE, current_base_branch_name()),
        prefix="update_",
        update_from_git=False,
        install_test_python_modules=False,
        update=update,
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
    base_version = request.param
    logger.info("Setting up test-site ...")
    return _get_site(base_version, update=False)


def update_site(target_version: str) -> Site:
    return _get_site(target_version, update=True)
