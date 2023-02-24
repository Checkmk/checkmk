#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.type("update")
def test_update(test_site):
    # get_site(os.getenv("TEST_UPDATE_SOURCE_RELEASE", "2.1.0p1"))
    # TODO: check source installation
    # TODO: set config
    # TODO: get baseline monitoring data
    # get_site(os.getenv("TEST_UPDATE_TARGET_RELEASE", "2.1.0p21"), update=True)
    # TODO: check target installation
    # TODO: check config
    # TODO: compare baseline monitoring data

    pass
