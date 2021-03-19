#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.check_legacy_includes.bonding import _check_ieee_302_3ad_specific  # type: ignore[attr-defined]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params, status, result", [
    (
        {
            'ieee_302_3ad_agg_id_missmatch_state': 1
        },
        {
            'aggregator_id': u'1',
            'interfaces': {
                u'ens1f0': {
                    'aggregator_id': u'1',
                },
                u'ens1f1': {
                    'aggregator_id': u'1',
                }
            },
        },
        [],
    ),
    (
        {
            'ieee_302_3ad_agg_id_missmatch_state': 1
        },
        {
            'aggregator_id': u'1',
            'interfaces': {
                u'ens1f0': {
                    'aggregator_id': u'1',
                },
                u'ens1f1': {
                    'aggregator_id': u'2',
                }
            },
        },
        [
            (1, "Missmatching aggregator ID of ens1f1: 2"),
        ],
    ),
    (
        {
            'ieee_302_3ad_agg_id_missmatch_state': 1
        },
        {
            'interfaces': {
                u'ens1f0': {
                    'aggregator_id': u'1',
                },
                u'ens1f1': {
                    'aggregator_id': u'1',
                }
            },
        },
        [],
    ),
    (
        {
            'ieee_302_3ad_agg_id_missmatch_state': 2
        },
        {
            'interfaces': {
                u'ens1f0': {
                    'aggregator_id': u'1',
                },
                u'ens1f1': {
                    'aggregator_id': u'2',
                }
            },
        },
        [
            (2, "Missmatching aggregator ID of ens1f1: 2"),
        ],
    ),
])
def test_check_ieee_302_3ad_specific(params, status, result):
    assert list(_check_ieee_302_3ad_specific(params, status)) == result
