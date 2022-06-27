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

from tests.testlib import on_time

from . import generictests


# Making this a single test with a loop instead of a parameterized test cuts down the runtime
# from 9.2s to 4.9s. Furthermore, freezing the time only once is a big win, too.
def test_dataset(fix_plugin_legacy) -> None:
    with on_time(1572247138, "CET"):
        for datasetname in generictests.DATASET_NAMES:
            dataset = import_module(f"tests.unit.checks.generictests.datasets.{datasetname}")
            generictests.run(fix_plugin_legacy.check_info, dataset)
