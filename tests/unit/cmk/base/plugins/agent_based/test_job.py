#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from copy import copy
import itertools
from typing import List, Union
import pytest  # type: ignore[import]

from testlib import on_time

from cmk.base.plugins.agent_based import job
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    clusterize,
    Result,
    State as state,
    Metric,
    type_defs,
)

SECTION_1: job.Section = {
    'SHREK': {
        'running': False,
        'start_time': 1547301201,
        'exit_code': 0,
        'metrics': {
            'real_time': 120.0,
            'user_time': 1.0,
            'system_time': 0.0,
            'reads': 0,
            'writes': 0,
            'max_res_bytes': 1234000,
            'avg_mem_bytes': 1000,
            'invol_context_switches': 12,
            'vol_context_switches': 23,
        },
    },
    'SNOWWHITE': {
        'running': False,
        'start_time': 1557301201,
        'exit_code': 1,
        'running_start_time': [
            1557301261, 1557301321, 1557301381, 1557301441, 1537301501, 1557301561
        ],
        'metrics': {
            'real_time': 360.0,
            'user_time': 0.0,
            'system_time': 0.0,
            'reads': 0,
            'writes': 0,
            'max_res_bytes': 2224000,
            'avg_mem_bytes': 0,
            'invol_context_switches': 1,
            'vol_context_switches': 2,
        },
    },
}

SECTION_2: job.Section = {
    'backup.sh': {
        'running': False,
        'start_time': 1415204091,
        'exit_code': 0,
        'running_start_time': [1415205713],
        'metrics': {
            'real_time': 281.65,
            'user_time': 277.7,
            'system_time': 32.12,
            'reads': 0,
            'writes': 251792,
            'max_res_bytes': 130304000,
            'avg_mem_bytes': 0,
            'invol_context_switches': 16806,
            'vol_context_switches': 32779,
        },
    },
    'cleanup_remote_logs': {
        'running': False,
        'start_time': 1415153430,
        'exit_code': 0,
        'metrics': {
            'real_time': 9.9,
            'user_time': 8.85,
            'system_time': 0.97,
            'reads': 96,
            'writes': 42016,
            'max_res_bytes': 11456000,
            'avg_mem_bytes': 0,
            'invol_context_switches': 15,
            'vol_context_switches': 274,
        },
    },
}

TIME = 1594300620.0, "CET"


def _modify_start_time(
    j: job.Job,
    start_time: Union[float, List[int]],
) -> job.Job:
    new_job: job.Job = copy(j)
    if isinstance(start_time, list):
        new_job['running_start_time'] = start_time
    else:
        new_job['start_time'] = start_time
    return new_job


@pytest.mark.parametrize("timestr,expected_result", [
    ('0:00.00', 0.),
    ('1:02.00', 62.),
    ('35:30:2.12', 35 * 60**2 + 30 * 60 + 2.12),
])
def test_job_parse_real_time(timestr, expected_result):
    assert job._job_parse_real_time(timestr) == expected_result


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    (
        [
            ['==>', 'SHREK', '<=='],
            ['start_time', '1547301201'],
            ['exit_code', '0'],
            ['real_time', '2:00.00'],
            ['user_time', '1.00'],
            ['system_time', '0.00'],
            ['reads', '0'],
            ['writes', '0'],
            ['max_res_kbytes', '1234'],
            ['avg_mem_kbytes', '1'],
            ['invol_context_switches', '12'],
            ['vol_context_switches', '23'],
            ['==>', 'SNOWWHITE', '<=='],
            ['start_time', '1557301201'],
            ['exit_code', '1'],
            ['real_time', '6:00.00'],
            ['user_time', '0.00'],
            ['system_time', '0.00'],
            ['reads', '0'],
            ['writes', '0'],
            ['max_res_kbytes', '2224'],
            ['avg_mem_kbytes', '0'],
            ['invol_context_switches', '1'],
            ['vol_context_switches', '2'],
            ['==>', 'SNOWWHITE.27997running', '<=='],
            ['start_time', '1557301261'],
            ['==>', 'SNOWWHITE.28912running', '<=='],
            ['start_time', '1557301321'],
            ['==>', 'SNOWWHITE.29381running', '<=='],
            ['start_time', '1557301381'],
            ['==>', 'SNOWWHITE.30094running', '<=='],
            ['start_time', '1557301441'],
            ['==>', 'SNOWWHITE.30747running', '<=='],
            ['start_time', '1537301501'],
            ['==>', 'SNOWWHITE.31440running', '<=='],
            ['start_time', '1557301561'],
        ],
        SECTION_1,
    ),
    (
        [
            ['==>', 'backup.sh', '<=='],
            ['start_time', '1415204091'],
            ['exit_code', '0'],
            ['real_time', '4:41.65'],
            ['user_time', '277.70'],
            ['system_time', '32.12'],
            ['reads', '0'],
            ['writes', '251792'],
            ['max_res_kbytes', '130304'],
            ['avg_mem_kbytes', '0'],
            ['invol_context_switches', '16806'],
            ['vol_context_switches', '32779'],
            ['==>', 'backup.sh.running', '<=='],
            ['start_time', '1415205713'],
            ['==>', 'cleanup_remote_logs', '<=='],
            ['start_time', '1415153430'],
            ['exit_code', '0'],
            ['real_time', '0:09.90'],
            ['user_time', '8.85'],
            ['system_time', '0.97'],
            ['reads', '96'],
            ['writes', '42016'],
            ['max_res_kbytes', '11456'],
            ['avg_mem_kbytes', '0'],
            ['invol_context_switches', '15'],
            ['vol_context_switches', '274'],
        ],
        SECTION_2,
    ),
])
def test_parse(string_table, expected_parsed_data):
    assert job.parse_job(string_table) == expected_parsed_data


RESULTS_SHREK: List[Union[Metric, Result]] = [
    Result(state=state.OK, summary='Latest exit code: 0'),
    Result(state=state.OK, summary='Real time: 2 minutes 0 seconds'),
    Metric('real_time', 120.0),
    Result(state=state.OK, notice='Latest job started at Jan 12 2019 14:53:21'),
    Metric('start_time', 1547301201.0),
    Result(state=state.OK, summary='Job age: 1 year 178 days'),
    Result(state=state.OK, notice='Avg. memory: 1000 B'),
    Metric('avg_mem_bytes', 1000.0),
    Result(state=state.OK, notice='Invol. context switches: 12'),
    Metric('invol_context_switches', 12.0),
    Result(state=state.OK, notice='Max. memory: 1.18 MiB'),
    Metric('max_res_bytes', 1234000.0),
    Result(state=state.OK, notice='Filesystem reads: 0'),
    Metric('reads', 0.0),
    Result(state=state.OK, notice='System time: 0 seconds'),
    Metric('system_time', 0.0),
    Result(state=state.OK, notice='User time: 1 second'),
    Metric('user_time', 1.0),
    Result(state=state.OK, notice='Vol. context switches: 23'),
    Metric('vol_context_switches', 23.0),
    Result(state=state.OK, notice='Filesystem writes: 0'),
    Metric('writes', 0.0),
]


def _aggr_shrek_result(node: str) -> Result:
    return Result(**dict(
        zip(  # type: ignore
            ("state", "notice"),
            clusterize.aggregate_node_details(node, RESULTS_SHREK),
        )))


@pytest.mark.parametrize(
    "job_data, age_levels, exit_code_to_state_map, expected_results",
    [
        (
            SECTION_1['SHREK'],
            (0, 0),
            {
                0: state.OK
            },
            RESULTS_SHREK,
        ),
        (
            SECTION_1['SHREK'],
            (1, 2),
            {
                0: state.OK
            },
            itertools.chain(
                RESULTS_SHREK[0:5],
                [
                    Result(
                        state=state.CRIT,
                        summary='Job age: 1 year 178 days (warn/crit at 1 second/2 seconds)',
                    ),
                ],
                RESULTS_SHREK[6:],
            ),
        ),
        (
            SECTION_1['SHREK'],
            (0, 0),
            {
                0: state.WARN
            },
            itertools.chain(
                [
                    Result(
                        state=state.WARN,
                        summary='Latest exit code: 0',
                    ),
                ],
                RESULTS_SHREK[1:],
            ),
        ),
        (
            _modify_start_time(
                SECTION_1['SHREK'],
                [1557301261, 1557301321, 1557301381, 1557301441, 1537301501, 1557301561],
            ),
            (1, 2),
            {
                0: state.OK
            },
            itertools.chain(
                RESULTS_SHREK[:3],
                [
                    Result(
                        state=state.OK,
                        notice=('6 jobs are currently running, started at'
                                ' May 08 2019 09:41:01, May 08 2019 09:42:01,'
                                ' May 08 2019 09:43:01, May 08 2019 09:44:01,'
                                ' Sep 18 2018 22:11:41, May 08 2019 09:46:01'),
                    ),
                    Result(
                        state=state.CRIT,
                        summary=('Job age (currently running): '
                                 '1 year 63 days (warn/crit at 1 second/2 seconds)'),
                    ),
                ],
                RESULTS_SHREK[6:],
            ),
        ),
    ],
)
def test_process_job_stats(
    job_data,
    age_levels,
    exit_code_to_state_map,
    expected_results,
):
    with on_time(*TIME):
        assert list(job._process_job_stats(
            job_data,
            age_levels,
            exit_code_to_state_map,
        )) == list(expected_results)


@pytest.mark.parametrize(
    "item, params, section, expected_results",
    [
        (
            'SHREK',
            type_defs.Parameters({'age': (0, 0)},),
            SECTION_1,
            RESULTS_SHREK,
        ),
        (
            'item',
            type_defs.Parameters({'age': (0, 0)},),
            {
                'item': {}
            },
            [Result(state=state.UNKNOWN, summary='Got incomplete information for this job')],
        ),
        (
            'cleanup_remote_logs',
            type_defs.Parameters({'age': (0, 0)},),
            SECTION_2,
            [
                Result(state=state.OK, summary='Latest exit code: 0',
                       details='Latest exit code: 0'),
                Result(state=state.OK, summary='Real time: 10 seconds'),
                Metric('real_time', 9.9),
                Result(state=state.OK, notice='Latest job started at Nov 05 2014 03:10:30'),
                Metric('start_time', 1415153430.0),
                Result(state=state.OK, summary='Job age: 5 years 248 days'),
                Result(state=state.OK, notice='Avg. memory: 0 B'),
                Metric('avg_mem_bytes', 0.0),
                Result(state=state.OK, notice='Invol. context switches: 15'),
                Metric('invol_context_switches', 15.0),
                Result(state=state.OK, notice='Max. memory: 10.9 MiB'),
                Metric('max_res_bytes', 11456000.0),
                Result(state=state.OK, notice='Filesystem reads: 96'),
                Metric('reads', 96.0),
                Result(state=state.OK, notice='System time: 970 milliseconds'),
                Metric('system_time', 0.97),
                Result(state=state.OK, notice='User time: 9 seconds'),
                Metric('user_time', 8.85),
                Result(state=state.OK, notice='Vol. context switches: 274'),
                Metric('vol_context_switches', 274.0),
                Result(state=state.OK, notice='Filesystem writes: 42016'),
                Metric('writes', 42016.0),
            ],
        ),
        (
            'backup.sh',
            type_defs.Parameters({'age': (1, 2)},),
            SECTION_2,
            [
                Result(state=state.OK, summary='Latest exit code: 0'),
                Result(state=state.OK, summary='Real time: 4 minutes 42 seconds'),
                Metric('real_time', 281.65),
                Result(state=state.OK,
                       notice='1 job is currently running, started at Nov 05 2014 17:41:53'),
                Result(
                    state=state.CRIT,
                    summary=
                    'Job age (currently running): 5 years 247 days (warn/crit at 1 second/2 seconds)'
                ),
                Result(state=state.OK, notice='Avg. memory: 0 B'),
                Metric('avg_mem_bytes', 0.0),
                Result(state=state.OK, notice='Invol. context switches: 16806'),
                Metric('invol_context_switches', 16806.0),
                Result(state=state.OK, notice='Max. memory: 124 MiB'),
                Metric('max_res_bytes', 130304000.0),
                Result(state=state.OK, notice='Filesystem reads: 0'),
                Metric('reads', 0.0),
                Result(state=state.OK, notice='System time: 32 seconds'),
                Metric('system_time', 32.12),
                Result(state=state.OK, notice='User time: 4 minutes 38 seconds'),
                Metric('user_time', 277.7),
                Result(state=state.OK, notice='Vol. context switches: 32779'),
                Metric('vol_context_switches', 32779.0),
                Result(state=state.OK, notice='Filesystem writes: 251792'),
                Metric('writes', 251792.0),
            ],
        ),
        (
            'missing',
            type_defs.Parameters({'age': (1, 2)},),
            SECTION_2,
            [],
        ),
    ],
)
def test_check_job(item, params, section, expected_results):
    with on_time(*TIME):
        assert list(job.check_job(item, params, section)) == expected_results


@pytest.mark.parametrize(
    "item, params, section, expected_results",
    [
        (
            'SHREK',
            type_defs.Parameters({'age': (0, 0)},),
            {
                'node1': SECTION_1
            },
            [
                _aggr_shrek_result('node1'),
                Result(
                    state=state.OK,
                    summary=
                    '1 node in state OK, 0 nodes in state WARN, 0 nodes in state CRIT, 0 nodes in state UNKNOWN',
                ),
            ],
        ),
        (
            'SHREK',
            type_defs.Parameters({'age': (0, 0)},),
            {
                'node1': SECTION_1,
                'node2': SECTION_1,
            },
            [
                _aggr_shrek_result('node1'),
                _aggr_shrek_result('node2'),
                Result(
                    state=state.OK,
                    summary=
                    '2 nodes in state OK, 0 nodes in state WARN, 0 nodes in state CRIT, 0 nodes in state UNKNOWN',
                ),
            ],
        ),
        (
            'SHREK',
            type_defs.Parameters({
                'age': (3600, 7200),
                'outcome_on_cluster': 'best',
            },),
            {
                'node1': SECTION_1,
                'node2': {
                    'SHREK': _modify_start_time(
                        SECTION_1['SHREK'],
                        1594293430.9147654,
                    ),
                },
            },
            [
                Result(state=state.OK,
                       notice=('[node1]: Latest exit code: 0\n'
                               '[node1]: Real time: 2 minutes 0 seconds\n'
                               '[node1]: Latest job started at Jan 12 2019 14:53:21\n'
                               '[node1]: Job age: 1 year 178 days (warn/crit at 1 hour'
                               ' 0 minutes/2 hours 0 minutes)(!!)\n'
                               '[node1]: Avg. memory: 1000 B\n'
                               '[node1]: Invol. context switches: 12\n'
                               '[node1]: Max. memory: 1.18 MiB\n'
                               '[node1]: Filesystem reads: 0\n'
                               '[node1]: System time: 0 seconds\n'
                               '[node1]: User time: 1 second\n'
                               '[node1]: Vol. context switches: 23\n'
                               '[node1]: Filesystem writes: 0')),
                Result(state=state.OK,
                       notice=('[node2]: Latest exit code: 0\n'
                               '[node2]: Real time: 2 minutes 0 seconds\n'
                               '[node2]: Latest job started at Jul 09 2020 13:17:10\n'
                               '[node2]: Job age: 1 hour 59 minutes (warn/crit at 1 hour'
                               ' 0 minutes/2 hours 0 minutes)(!)\n'
                               '[node2]: Avg. memory: 1000 B\n'
                               '[node2]: Invol. context switches: 12\n'
                               '[node2]: Max. memory: 1.18 MiB\n'
                               '[node2]: Filesystem reads: 0\n'
                               '[node2]: System time: 0 seconds\n'
                               '[node2]: User time: 1 second\n'
                               '[node2]: Vol. context switches: 23\n'
                               '[node2]: Filesystem writes: 0')),
                Result(state=state.WARN,
                       summary=('0 nodes in state OK, 1 node in state WARN,'
                                ' 1 node in state CRIT, 0 nodes in state UNKNOWN')),
            ],
        ),
        (
            'missing',
            type_defs.Parameters({'age': (0, 0)},),
            {
                'node1': SECTION_1,
                'node2': SECTION_2,
            },
            [
                Result(
                    state=state.UNKNOWN,
                    summary='Received no data for this job from any of the nodes',
                ),
            ],
        ),
    ],
)
def test_cluster_check_job(item, params, section, expected_results):
    with on_time(*TIME):
        assert list(job.cluster_check_job(item, params, section)) == expected_results
