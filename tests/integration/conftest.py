#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from tests.testlib.site import get_site_factory


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True)
def site(request):
    sf = get_site_factory(prefix="int_", update_from_git=True, install_test_python_modules=True)
    return sf.get_existing_site("test")
