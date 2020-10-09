#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.gui.plugins.wato.check_parameters.domino_tasks import _transform_inv_domino_tasks_rules


@pytest.mark.parametrize("params, transformed_params", [
    (
        {
            'descr': 'abc',
            'match': 'foo',
            'levels': (1, 2, 3, 4)
        },
        {
            'descr': 'abc',
            'match': 'foo',
            'default_params': {
                'levels': (1, 2, 3, 4)
            }
        },
    ),
    (
        {
            'descr': 'abc',
            'match': 'foo',
            'default_params': {
                'levels': (1, 2, 3, 4)
            }
        },
        {
            'descr': 'abc',
            'match': 'foo',
            'default_params': {
                'levels': (1, 2, 3, 4)
            }
        },
    ),
])
def test_transform_discovery_params(params, transformed_params):
    assert _transform_inv_domino_tasks_rules(params) == transformed_params
