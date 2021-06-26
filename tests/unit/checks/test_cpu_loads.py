#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.plugins.agent_based.utils.cpu import Section, Load
from cmk.base.plugins.agent_based.cpu_load import check_cpu_load
from cmk.base.api.agent_based.checking_classes import State, Metric, Result

pytestmark = pytest.mark.checks


def test_cpu_loads_fixed_levels(mocker):
    section = Section(load=Load(0.5, 1.0, 1.5), num_cpus=4, num_threads=123)
    params = {'levels': (2.0, 4.0)}
    result = set(check_cpu_load(params, section))
    assert result == set((
        Result(state=State.OK, summary='15 min load: 1.50'),
        Result(state=State.OK, summary='15 min load per core: 0.38 (4 cores)'),
        Metric('load1', 0.5, boundaries=(0, 4.0)),
        Metric('load5', 1.0, boundaries=(0, 4.0)),
        Metric('load15', 1.5, levels=(8.0, 16.0)),  # levels multiplied by num_cpus
    ))


def test_cpu_loads_predictive(mocker):
    # make sure cpu_load check can handle predictive values
    mocker.patch("cmk.base.check_api._prediction.get_levels",
                 return_value=(None, (2.2, 4.2, None, None)))
    # TODO: don't mock this. Use the context managers.
    mocker.patch("cmk.base.plugin_contexts._hostname", value="unittest")
    mocker.patch("cmk.base.plugin_contexts._service_description", value="unittest-sd")
    params = {
        'levels': {
            'period': 'minute',
            'horizon': 1,
            'levels_upper': ('absolute', (2.0, 4.0))
        }
    }
    section = Section(load=Load(0.5, 1.0, 1.5), num_cpus=4, num_threads=123)
    result = set(check_cpu_load(params, section))

    assert result == set((
        Result(state=State.OK, summary='15 min load: 1.50 (no reference for prediction yet)'),
        Result(state=State.OK, summary='15 min load per core: 0.38 (4 cores)'),
        Metric('load1', 0.5, boundaries=(0, 4.0)),
        Metric('load5', 1.0, boundaries=(0, 4.0)),
        Metric('load15', 1.5, levels=(2.2, 4.2)),  # those are the predicted values
    ))
