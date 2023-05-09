#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from generictests.crashtest import CrashReportList
from generictests import DATASET_FILES


def pytest_addoption(parser):
    parser.addoption("--datasetfile", action="store", default=None)
    parser.addoption("--crashstates", action="store", default="")
    parser.addoption("--inplace", action="store_true", default=False)


def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    if 'datasetfile' in metafunc.fixturenames:
        if metafunc.config.option.datasetfile is not None:
            metafunc.parametrize('datasetfile', [metafunc.config.option.datasetfile])
        elif metafunc.config.option.inplace:
            metafunc.parametrize('datasetfile', [str(f) for f in DATASET_FILES])

    if 'crashdata' in metafunc.fixturenames and metafunc.config.option.crashstates is not None:
        crash_reports = CrashReportList(metafunc.config.option.crashstates)
        metafunc.parametrize('crashdata', crash_reports, ids=[r.crash_id for r in crash_reports])

    if 'inplace' in metafunc.fixturenames:
        metafunc.parametrize('inplace', [metafunc.config.option.inplace])
