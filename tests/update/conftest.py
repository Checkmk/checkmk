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
    BASE_VERSIONS = ["2.1.0p1", "2.1.0p2"]
    IDS = [f"base-version: {base_version}" for base_version in BASE_VERSIONS]


@pytest.fixture(name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS)
def get_site(request: pytest.FixtureRequest, update: bool = False, stop: bool = True) -> Site:
    base_version = request.param
    logger.info("Setting up test-site ...")

    # we need to provide the version here for install-cmk.py
    os.environ["VERSION"] = base_version

    # we need to skip the enforce_non_localized_gui() call since it will fail for older releases
    os.environ["SKIP_ENFORCE_NON_LOCALIZED_GUI"] = "1"

    sf = SiteFactory(
        version=CMKVersion(base_version, Edition.CEE, current_base_branch_name()),
        prefix="update_",
        update_from_git=False,
        install_test_python_modules=False,
        update=update,
    )
    site_to_return = sf.get_existing_site("central")

    logger.info("Site exists=%s", site_to_return.exists())
    if site_to_return.exists():
        if not update:
            logger.info("Dropping existing site")
            site_to_return.rm()
        elif site_to_return.is_running() and stop:
            logger.info("Stopping running site before update")
            site_to_return.stop()
    logger.info("Creating new site")
    site_to_return = sf.get_site("central")
    logger.info("Testsite %s is up", site_to_return.id)

    return site_to_return
