#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import os
from typing import Iterator

import pytest

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_branch_name
from tests.testlib.version import CMKVersion

site_number = 0


# Disable this. We have a site_factory instead.
@pytest.fixture(scope="module")
def site(request):
    pass


# The scope of the site factory is "module" to avoid that changing the site properties in a module
# may result in a test failing in another one
@pytest.fixture(scope="module")
def site_factory() -> Iterator[SiteFactory]:
    # Using a different site for every module to avoid having issues when saving the results for the
    # tests: if you call SiteFactory.save_results() twice with the same site_id, it will crash
    # because the results are already there.
    global site_number
    sf = SiteFactory(
        version=os.environ.get("VERSION", CMKVersion.DAILY),
        edition=os.environ.get("EDITION", CMKVersion.CEE),
        branch=os.environ.get("BRANCH") or current_branch_name(),
        prefix=f"comp_{site_number}_",
    )
    site_number += 1
    try:
        yield sf
    finally:
        sf.save_results()
        sf.cleanup()


@pytest.fixture(scope="module")
def central_site(site_factory: SiteFactory) -> Site:  # type:ignore[no-untyped-def]
    return site_factory.get_site("central")
