#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


####################################################################################
# NOTE: This is considered as a workaround file and is intended to removed
# in the future.
####################################################################################


import unittest

import pytest
import pytest_mock

# pylint: disable=comparison-with-callable,redefined-outer-name


@pytest.fixture
def write_sections_mock(mocker: pytest_mock.MockFixture) -> unittest.mock.MagicMock:
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")
