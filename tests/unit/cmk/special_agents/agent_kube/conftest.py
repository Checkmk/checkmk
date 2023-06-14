#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


####################################################################################
# NOTE: This is considered as a workaround file and is intended to removed
# in the future.
####################################################################################


import unittest

import pytest
import pytest_mock


@pytest.fixture(name="write_sections_mock")
def fixture_write_sections_mock(mocker: pytest_mock.MockFixture) -> unittest.mock.MagicMock:
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")


@pytest.fixture(name="write_writeable_sections_mock")
def fixture_write_writeable_sections_mock(
    mocker: pytest_mock.MockFixture,
) -> unittest.mock.MagicMock:
    return mocker.patch("cmk.special_agents.utils_kubernetes.common.write_sections")
