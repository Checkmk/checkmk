#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.repo import current_base_branch_name
from tests.testlib.site import get_site_factory, Site
from tests.testlib.version import CMKVersion

from cmk.utils.version import Edition


@pytest.fixture(name="site", scope="session")
def fixture_site() -> Iterator[Site]:
    yield from get_site_factory(
        prefix="ext_comp_",
        fallback_branch=current_base_branch_name,
    ).get_test_site(name=current_base_branch_name().replace(".", "").replace("0", ""))


@pytest.fixture(name="site22", scope="session")
def fixture_site22() -> Iterator[Site]:
    yield from get_site_factory(
        version=CMKVersion(CMKVersion.DAILY, Edition.CEE, "2.2.0", "2.2.0"),
        prefix="ext_comp_",
    ).get_test_site(name="22")
