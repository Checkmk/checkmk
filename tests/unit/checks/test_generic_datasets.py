#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

import datetime
from importlib import import_module
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.unit.mocks_and_helpers import FixPluginLegacy

from . import generictests

# Making this a single test with a loop instead of a parameterized test cuts down the runtime
# from 15.7s to 4.3s. Furthermore, freezing the time only once is a big win, too. OTOH, if
# something goes wrong, pinning down the exact dataset is very helpful, so we use the "slow"
# marker below for the latter use case.


def test_all_datasets(fix_plugin_legacy: FixPluginLegacy) -> None:
    with time_machine.travel(
        datetime.datetime.fromtimestamp(1572247138, tz=ZoneInfo("CET")), tick=False
    ):
        for datasetname in generictests.DATASET_NAMES:
            run_tests_for(datasetname, fix_plugin_legacy)


@pytest.mark.slow
@pytest.mark.parametrize("datasetname", generictests.DATASET_NAMES)
def test_dataset_one_by_one(datasetname: str, fix_plugin_legacy: FixPluginLegacy) -> None:
    with time_machine.travel(
        datetime.datetime.fromtimestamp(1572247138, tz=ZoneInfo("CET")), tick=False
    ):
        run_tests_for(datasetname, fix_plugin_legacy)


def run_tests_for(datasetname: str, fix_plugin_legacy: FixPluginLegacy) -> None:
    dataset = import_module(f"tests.unit.checks.generictests.datasets.{datasetname}")
    generictests.run(fix_plugin_legacy.check_info, dataset)
