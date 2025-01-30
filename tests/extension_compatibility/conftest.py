#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from tests.testlib.common.repo import current_base_branch_name
from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site


@pytest.fixture(name="site", scope="session")
def fixture_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from get_site_factory(
            prefix="ext_comp_",
            fallback_branch=current_base_branch_name,
        ).get_test_site(name="1")
