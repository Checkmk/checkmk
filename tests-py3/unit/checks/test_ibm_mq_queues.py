#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.check_api import MKCounterWrapped
from test_ibm_mq_include import parse_info

pytestmark = pytest.mark.checks

CHECK_NAME = "ibm_mq_queues"


def test_parse(check_manager):
    lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.


AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE.ONE)
   TYPE(QLOCAL)                            MAXDEPTH(5000)
AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE.TWO)
   TYPE(QLOCAL)                            MAXDEPTH(200000)
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE.ONE)
   TYPE(QUEUE)                             CURDEPTH(0)
   LGETDATE( )                             LGETTIME( )
   LPUTDATE( )                             LPUTTIME( )
   MONQ(MEDIUM)                            MSGAGE(0)
   QTIME( , )
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE.TWO)
   TYPE(QUEUE)                             CURDEPTH(1400)
   LGETDATE(2017-03-09)                    LGETTIME(08.49.13)
   LPUTDATE( )                             LPUTTIME( )
   OPPROCS(0)                              IPPROCS(5)
   MONQ(MEDIUM)                            MSGAGE(2201)
   QTIME(999999999, 999999999)
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
    section = parse_info(lines, chr(10))
    check = check_manager.get_check(CHECK_NAME)
    parsed = check.run_parse(section)
    assert 2 + 1 == len(parsed)

    attrs = parsed['MY.TEST']
    assert attrs['STATUS'] == 'RUNNING'
    assert attrs['NOW'] is not None

    attrs = parsed['MY.TEST:MY.QUEUE.TWO']
    assert attrs['CURDEPTH'] == '1400'
    assert attrs['LGETDATE'] == '2017-03-09'
    assert attrs['LGETTIME'] == '08.49.13'
    assert attrs['CURDEPTH'] == '1400'
    assert attrs['MAXDEPTH'] == '200000'
    assert attrs['MSGAGE'] == '2201'


def test_discovery_qmgr_not_included(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM2': {
            'STATUS': 'RUNNING'
        },
        'QM1:QUEUE1': {
            'CURDEPTH': '0'
        },
        'QM1:QUEUE2': {
            'CURDEPTH': '1400'
        },
        'QM2:QUEUE3': {
            'CURDEPTH': '530'
        },
        'QM2:QUEUE4': {
            'CURDEPTH': '10'
        },
    }
    discovery = list(check.run_discovery(parsed))
    assert len(discovery) == 4
    assert ('QM1:QUEUE2', {}) in discovery
    assert ('QM2:QUEUE3', {}) in discovery


def test_check(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = {'curdepth': (1500, 2000), 'ipprocs': {'upper': (4, 8)}}
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:MY.QUEUE': {
            'CURDEPTH': '1400',
            'MAXDEPTH': '200000',
            'MSGAGE': '2201',
            'IPPROCS': '5',
            'OPPROCS': '0',
        }
    }
    actual = list(check.run_check('QM1:MY.QUEUE', params, parsed))
    expected = [(0, 'Queue depth: 1400 (0.7%)', [('messages_in_queue', 1400, 1500, 2000, 0, 200000)
                                                ]),
                (0, 'Oldest message: 36 m', [('age_oldest', 2201, None, None)]),
                (1, 'Open input count: 5 (warn/crit at 4/8)', [('reading', 5, 4, 8)]),
                (0, 'Open output count: 0', [('writing', 0, None, None)])]
    assert actual == expected


def test_stale_service_for_not_running_qmgr(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = {}
    parsed = {'QM1': {'STATUS': 'ENDED NORMALLY'}}
    with pytest.raises(MKCounterWrapped, match=r"Stale because queue manager ENDED NORMALLY"):
        list(check.run_check('QM1:MY.QUEUE', params, parsed))


def test_vanished_service_for_running_qmgr(check_manager):
    check = check_manager.get_check(CHECK_NAME)
    params = {}
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:QUEUE1': {
            'CURDEPTH': '0'
        },
    }
    actual = list(check.run_check('QM1:VANISHED', params, parsed))
    assert len(actual) == 0


#
# CURDEPTH, MAXDEPTH
#
def test_depth_no_params(check_manager):
    params = {}
    curdepth, maxdepth = 0, 5000
    expected = (0, 'Queue depth: 0', [('messages_in_queue', 0, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_with_percentage(check_manager):
    params = {}
    curdepth, maxdepth = 50, 5000
    expected = (0, 'Queue depth: 50 (1.0%)', [('messages_in_queue', 50, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_no_max_depth(check_manager):
    params = {}
    curdepth, maxdepth = 50, None
    expected = (0, 'Queue depth: 50', [('messages_in_queue', 50, None, None, 0, None)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_ok(check_manager):
    params = {'curdepth': (100, 500)}
    curdepth, maxdepth = 50, 5000
    expected = (0, 'Queue depth: 50 (1.0%)', [('messages_in_queue', 50, 100, 500, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_warn(check_manager):
    params = {'curdepth': (100, 500)}
    curdepth, maxdepth = 100, 5000
    expected = (1, 'Queue depth: 100 (2.0%) (warn/crit at 100/500)', [('messages_in_queue', 100,
                                                                       100, 500, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_crit(check_manager):
    params = {'curdepth': (100, 500)}
    curdepth, maxdepth = 500, 5000
    expected = (2, 'Queue depth: 500 (10.0%) (warn/crit at 100/500)', [('messages_in_queue', 500,
                                                                        100, 500, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_percentage_ok(check_manager):
    params = {'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 50, 5000
    expected = (0, 'Queue depth: 50 (1.0%)', [('messages_in_queue', 50, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_percentage_warn(check_manager):
    params = {'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 4000, 5000
    expected = (1, 'Queue depth: 4000 (80.0%) (warn/crit at 80.0%/90.0%)',
                [('messages_in_queue', 4000, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_percentage_error(check_manager):
    params = {'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 4900, 5000
    expected = (2, 'Queue depth: 4900 (98.0%) (warn/crit at 80.0%/90.0%)',
                [('messages_in_queue', 4900, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_percentage_ignored_in_wato(check_manager):
    params = {'curdepth_perc': (None, None)}
    curdepth, maxdepth = 4900, 5000
    expected = (0, 'Queue depth: 4900 (98.0%)', [('messages_in_queue', 4900, None, None, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_both_ok(check_manager):
    params = {'curdepth': (100, 500), 'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 50, 5000
    expected = (0, 'Queue depth: 50 (1.0%)', [('messages_in_queue', 50, 100, 500, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_one_of_them_warn(check_manager):
    params = {'curdepth': (100, 500), 'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 100, 5000
    expected = (1, 'Queue depth: 100 (2.0%) (warn/crit at 100/500)', [('messages_in_queue', 100,
                                                                       100, 500, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def test_depth_param_one_warn_one_crit(check_manager):
    params = {'curdepth': (100, 4950), 'curdepth_perc': (80.0, 90.0)}
    curdepth, maxdepth = 4900, 5000
    expected = (2, 'Queue depth: 4900 (98.0%) (warn/crit at 100/4950 and 80.0%/90.0%)',
                [('messages_in_queue', 4900, 100, 4950, 0, 5000)])
    assert_depth(check_manager, curdepth, maxdepth, params, expected)


def assert_depth(check_manager, curdepth, maxdepth, params, expected):
    check = check_manager.get_check(CHECK_NAME)
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:MY.QUEUE': {
            'CURDEPTH': curdepth,
            'MAXDEPTH': maxdepth,
            'MSGAGE': '2201',
            'IPPROCS': '5',
            'OPPROCS': '0',
        }
    }
    actual = list(check.run_check('QM1:MY.QUEUE', params, parsed))
    assert expected == actual[0]


#
# MSGAGE
#


def test_age_no_params(check_manager):
    params = {}
    msgage = 1800
    expected = (0, 'Oldest message: 30 m', [('age_oldest', 1800, None, None)])
    assert_age(check_manager, msgage, params, expected)


def test_age_no_msgage(check_manager):
    params = {}
    msgage = None
    expected = (0, 'Oldest message: n/a', [])
    assert_age(check_manager, msgage, params, expected)


def test_age_ok(check_manager):
    params = {'msgage': (1800, 3600)}
    msgage = 1200
    expected = (0, 'Oldest message: 20 m', [('age_oldest', 1200, 1800, 3600)])
    assert_age(check_manager, msgage, params, expected)


def test_age_warn(check_manager):
    params = {'msgage': (1800, 3600)}
    msgage = 1801
    expected = (1, 'Oldest message: 30 m (warn/crit at 30 m/60 m)', [('age_oldest', 1801, 1800,
                                                                      3600)])
    assert_age(check_manager, msgage, params, expected)


def test_age_crit(check_manager):
    params = {'msgage': (1800, 3600)}
    msgage = 3601
    expected = (2, 'Oldest message: 60 m (warn/crit at 30 m/60 m)', [('age_oldest', 3601, 1800,
                                                                      3600)])
    assert_age(check_manager, msgage, params, expected)


def assert_age(check_manager, msgage, params, expected):
    check = check_manager.get_check(CHECK_NAME)
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:MY.QUEUE': {
            'CURDEPTH': 13,
            'MAXDEPTH': 5000,
            'MSGAGE': msgage,
            'IPPROCS': '5',
            'OPPROCS': '0',
        }
    }
    actual = list(check.run_check('QM1:MY.QUEUE', params, parsed))
    assert expected == actual[1]


#
#  Last GET (or PUT) age
#


def test_lget_ok_no_params(check_manager):
    lget = ("2018-04-19", "10.19.05")
    now = ("2018-04-19", "11.19.05")
    params = {}
    expected = (0, 'Last get: 60 m', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def test_lget_ok_no_info(check_manager):
    lget = ("", "")
    now = ("2018-04-19", "11.19.05")
    params = {}
    expected = (0, 'Last get: n/a', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def test_lget_ok(check_manager):
    lget = ("2018-04-19", "10.19.05")
    now = ("2018-04-19", "10.19.15")
    params = {'lgetage': (1800, 3600)}
    expected = (0, 'Last get: 10.0 s', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def test_lget_warn(check_manager):
    lget = ("2018-04-19", "09.49.14")
    now = ("2018-04-19", "10.19.15")
    params = {'lgetage': (1800, 3600)}
    expected = (1, 'Last get: 30 m (warn/crit at 30 m/60 m)', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def test_lget_no_info_with_params(check_manager):
    lget = ("", "")
    now = ("2018-04-19", "10.19.15")
    params = {'lgetage': (1800, 3600)}
    expected = (0, 'Last get: n/a', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def test_lget_crit(check_manager):
    lget = ("2018-04-19", "09.19.14")
    now = ("2018-04-19", "10.19.15")
    params = {'lgetage': (1800, 3600)}
    expected = (2, 'Last get: 60 m (warn/crit at 30 m/60 m)', [])
    assert_last_get_age(check_manager, lget, now, params, expected)


def assert_last_get_age(check_manager, lget, now, params, expected):
    check = check_manager.get_check(CHECK_NAME)
    lgetdate, lgettime = lget
    reference_iso_time = "%sT%s+0200" % (now[0], now[1].replace('.', ':'))
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING',
            'NOW': reference_iso_time,
        },
        'QM1:MY.QUEUE': {
            'CURDEPTH': 0,
            'MAXDEPTH': 5000,
            'LGETDATE': lgetdate,
            'LGETTIME': lgettime,
        }
    }

    actual = list(check.run_check('QM1:MY.QUEUE', params, parsed))
    assert expected == actual[1]


#
# IPPROCS/OPPROCS
#


def test_procs_no_params(check_manager):
    params = {}
    opprocs = 3
    expected = (0, 'Open output count: 3', [('writing', 3, None, None)])
    assert_procs(check_manager, opprocs, params, expected)


def test_procs_upper(check_manager):
    params = {'opprocs': {'upper': (10, 20)}}

    opprocs = 3
    expected = (0, 'Open output count: 3', [('writing', 3, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 10
    expected = (1, 'Open output count: 10 (warn/crit at 10/20)', [('writing', 10, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 11
    expected = (1, 'Open output count: 11 (warn/crit at 10/20)', [('writing', 11, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 20
    expected = (2, 'Open output count: 20 (warn/crit at 10/20)', [('writing', 20, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 21
    expected = (2, 'Open output count: 21 (warn/crit at 10/20)', [('writing', 21, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)


def test_procs_lower(check_manager):
    params = {'opprocs': {'lower': (3, 1)}}

    opprocs = 3
    expected = (0, 'Open output count: 3', [('writing', 3, None, None)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 2
    expected = (1, 'Open output count: 2 (warn/crit below 3/1)', [('writing', 2, None, None)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 1
    expected = (1, 'Open output count: 1 (warn/crit below 3/1)', [('writing', 1, None, None)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 0
    expected = (2, 'Open output count: 0 (warn/crit below 3/1)', [('writing', 0, None, None)])
    assert_procs(check_manager, opprocs, params, expected)


def test_procs_lower_and_upper(check_manager):
    params = {
        'opprocs': {
            'lower': (3, 1),
            'upper': (10, 20),
        }
    }

    opprocs = 1
    expected = (1, 'Open output count: 1 (warn/crit below 3/1)', [('writing', 1, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 0
    expected = (2, 'Open output count: 0 (warn/crit below 3/1)', [('writing', 0, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)

    opprocs = 21
    expected = (2, 'Open output count: 21 (warn/crit at 10/20)', [('writing', 21, 10, 20)])
    assert_procs(check_manager, opprocs, params, expected)


def assert_procs(check_manager, opprocs, params, expected):
    check = check_manager.get_check(CHECK_NAME)
    parsed = {
        'QM1': {
            'STATUS': 'RUNNING'
        },
        'QM1:MY.QUEUE': {
            'CURDEPTH': 0,
            'MAXDEPTH': 5000,
            'OPPROCS': opprocs,
        }
    }
    actual = list(check.run_check('QM1:MY.QUEUE', params, parsed))
    assert expected == actual[1]
