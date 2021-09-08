#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from tests.testlib.site import SiteFactory
from tests.testlib.utils import current_branch_name
from tests.testlib.version import CMKVersion


# Disable this. We have a site_factory instead.
@pytest.fixture(scope="session")
def site(request):
    pass


@pytest.fixture(scope="session")
def site_factory():
    try:
        sf = SiteFactory(
            version=os.environ.get("VERSION", CMKVersion.DAILY),
            edition=os.environ.get("EDITION", CMKVersion.CEE),
            branch=os.environ.get("BRANCH", current_branch_name()),
            prefix="comp_",
        )
        yield sf
    finally:
        sf.save_results()
        sf.cleanup()
