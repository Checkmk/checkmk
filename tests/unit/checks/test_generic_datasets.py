#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Run all possible tests on every dataset found in generictests/datasets/

For simple check tests there is a framework which allows the creation of tests
via the definition of datasets.

These can be found in the subfolder ''checks/generictests/datasets'' of the
unittest folder.

In the most basic case, they define the ''checkname'' and ''info'' variable.
This will trigger a test run of the corresponding check using ''info'' as
argument to the parse or discovery function (see for example ''uptime_1.py'').
Without any further data, the test will be OK if the check does not crash.

If you also want to test for specific results you can either provide the
required variables manually (as in ''veritas_vcs_*.py''), or create a
regression test dataset as described in ''checks/generictests/regression.py''
"""
from importlib import import_module

import pytest

from tests.testlib import on_time

from . import generictests

pytestmark = pytest.mark.checks


# TODO: Shouldn't we enable this by default for all unit tests?
@pytest.fixture(name="mock_time", scope="module")
def fixture_mock_time():
    """Use this fixture for simple time + zone mocking

    Use this fixture instead of directly invoking on_time in case you don't need a specific time.
    Calling this once instead of on_time() a lot of times saves execution time.
    """
    with on_time(1572247138, "CET"):
        yield


@pytest.mark.usefixtures("mock_time")
@pytest.mark.parametrize("datasetname", generictests.DATASET_NAMES)
def test_dataset(datasetname, fix_plugin_legacy):
    dataset = import_module("tests.unit.checks.generictests.datasets.%s" % datasetname)
    generictests.run(fix_plugin_legacy.check_info, dataset)
