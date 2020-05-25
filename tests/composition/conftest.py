#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import print_function
import os
import pytest  # type: ignore[import]
from testlib import SiteFactory, CMKVersion, current_branch_name


# Disable this. We have a site_factory instead.
@pytest.fixture(scope="session")
def site(request):
    pass


@pytest.fixture(scope="session")
def site_factory():
    try:
        sf = SiteFactory(version=os.environ.get("VERSION", CMKVersion.DAILY),
                         edition=os.environ.get("EDITION", CMKVersion.CEE),
                         branch=os.environ.get("BRANCH", current_branch_name()),
                         prefix="comp_")
        yield sf
    finally:
        sf.cleanup()
