#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import (
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    TypedDict,
    Tuple,
    Union,
)
from .agent_based_api.v1 import (
    Metric,
    register,
    render,
    Result,
    Service,
    State as state,
    type_defs,
)
from .agent_based_api.v1.clusterize import aggregate_node_details

# <<<job>>>
# ==> asd ASD <==
# start_time 1389355839
# exit_code 0
# real_time 0:00.00
# user_time 0.00
# system_time 0.00
# reads 0
# writes 0
# max_res_kbytes 1968
# avg_mem_kbytes 0
#
#
# ==> test <==
# start_time 1389352839
# exit_code 0
# real_time 0:00.00
# user_time 0.00
# system_time 0.00
# reads 0
# writes 0
# max_res_kbytes 1984
# avg_mem_kbytes 0

Metrics = Dict[str, Union[int, float]]


class Job(TypedDict, total=False):
    running: bool
    exit_code: int
    start_time: float
    running_start_time: List[int]
    metrics: Metrics


Section = Dict[str, Job]


def _job_parse_real_time(s: str) -> float:
    parts = s.split(':')
    min_sec, hour_sec = 0, 0
    if len(parts) == 3:
        hour_sec = int(parts[0]) * 60 * 60
    if len(parts) >= 2:
        min_sec = int(parts[-2]) * 60
    return float(parts[-1]) + min_sec + hour_sec


def _job_parse_key_values(line: List[str]) -> Tuple[str, Union[int, float]]:
    key, val = line
    if key == 'real_time':
        return key, _job_parse_real_time(val)
    if key in ('user_time', 'system_time'):
        return key, float(val)
    if key in ('max_res_kbytes', 'avg_mem_kbytes'):
        return key.replace('kbytes', 'bytes'), int(val) * 1000
    return key, int(val)


def parse_job(string_table: type_defs.AgentStringTable) -> Section:
    parsed: Section = {}
    job: Job = {}
    for line in string_table:
        if line[0] == "==>" and line[-1] == "<==":
            jobname = " ".join(line[1:-1])
            running = jobname.endswith("running")
            if running:
                jobname = jobname.rsplit(".", 1)[0]

            metrics: Metrics = {}
            job = parsed.setdefault(
                jobname,
                {
                    "running": running,
                    "metrics": metrics,
                },
            )

        elif job and len(line) == 2:
            key, val = _job_parse_key_values(line)
            if running:
                job.setdefault('running_start_time', []).append(int(val))
            elif key == 'exit_code':
                job['exit_code'] = int(val)
            elif key == 'start_time':
                job['start_time'] = val
            else:
                assert key in _METRIC_SPECS
                metrics[key] = val

    return parsed


register.agent_section(
    name="job",
    parse_function=parse_job,
)


def discover_job(section: Section) -> Generator[Service, None, None]:
    for jobname, job in section.items():
        if not job["running"]:
            yield Service(item=jobname)


def _process_start_time(value: float, warn: int, crit: int) -> Tuple[state, str]:
    display_value = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))
    job_age = time.time() - value
    if crit and job_age >= crit:
        return state.CRIT, display_value + " (more than %s ago)" % render.timespan(crit)
    if warn and job_age >= warn:
        return state.WARN, display_value + " (more than %s ago)" % render.timespan(warn)
    return state.OK, display_value


def _normal_result(mon_state: state, summary: str) -> Result:
    return Result(state=mon_state, summary=summary)


def _ok_result(mon_state: state, summary: str) -> Result:
    return Result(state=state.OK, summary=summary)


_METRIC_SPECS: Mapping[str, Tuple[str, Callable]] = {
    'real_time': ('Real-Time', render.timespan),
    'user_time': ('User-Time', render.timespan),
    'system_time': ('System-Time', render.timespan),
    'reads': ('Filesystem Reads', str),
    'writes': ('Filesystem Writes', str),
    'max_res_bytes': ('Max. Memory', render.bytes),
    'avg_mem_bytes': ('Avg. Memory', render.bytes),
    'vol_context_switches': ('Vol. Context Switches', str),
    'invol_context_switches': ('Invol. Context Switches', str),
}


def _process_job_stats(
    job: Job,
    age_levels: Tuple[int, int],
    exit_code_to_state_map: List[Tuple[int, int]],
) -> Generator[Union[Result, Metric], None, None]:

    prefix = ''
    result_constructor = _normal_result
    if 'running_start_time' in job:
        prefix = 'Previous result (considered OK): '
        result_constructor = _ok_result
        mon_state, display_value = _process_start_time(
            min(job['running_start_time']),
            *age_levels,
        )
        yield Result(
            state=mon_state,
            summary='Currently running (started: %s)' % display_value,
        )

    exit_code_job = job['exit_code']
    txt = 'Exit-Code: %d' % exit_code_job

    for exit_code, mon_state_int in exit_code_to_state_map:
        if exit_code == exit_code_job:
            mon_state = state(mon_state_int)
            break
    else:
        mon_state = state.OK if exit_code_job == 0 else state.CRIT

    yield result_constructor(
        mon_state=mon_state,
        summary=prefix + txt,
    )

    if 'start_time' in job:
        mon_state, display_value = _process_start_time(job['start_time'], *age_levels)
        yield result_constructor(
            mon_state=mon_state,
            summary='%s: %s' % ('Started', display_value),
        )
        yield Metric('start_time', job['start_time'])

    for metric, val in job['metrics'].items():
        title, render_fun = _METRIC_SPECS[metric]
        yield Result(
            state=state.OK,
            summary='%s: %s' % (title, render_fun(val)),
        )
        yield Metric(metric, val)


def check_job(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> Generator[Union[Result, Metric], None, None]:

    job = section.get(item)
    if job is None:
        return

    if job.get("exit_code") is None:
        yield Result(
            state=state.UNKNOWN,
            summary='Got incomplete information for this job',
        )
        return

    yield from _process_job_stats(
        job,
        params['age'],
        params.get('exit_code_to_state_map', []),
    )


_STATE_TO_STR = {
    state.OK: 'OK',
    state.WARN: 'WARN',
    state.CRIT: 'CRIT',
    state.UNKNOWN: 'UNKNOWN',
}


def cluster_check_job(
    item: str,
    params: type_defs.Parameters,
    section: Dict[str, Section],
) -> Generator[Result, None, None]:
    """
    This check used to simply yield all metrics from all nodes, which is useless, since the user
    cannot interpret these numbers. For now, we do not yield any metrics until a better solution is
    found.
    """

    states: List[state] = []
    best_outcome = params.get("outcome_on_cluster") == "best"

    for node, node_section in section.items():
        node_state, node_text = aggregate_node_details(
            node,
            check_job(item, params, node_section),
        )
        if not node_text:
            continue

        states.append(node_state)
        yield Result(state=state.OK if best_outcome else node_state, notice=node_text)

    if states:
        summary = []
        for stat, stat_str in _STATE_TO_STR.items():
            n_in_state = states.count(stat)
            pluralize = '' if n_in_state == 1 else 's'
            summary.append('%d node%s in state %s' % (n_in_state, pluralize, stat_str))

        if best_outcome:
            yield Result(state=state.best(*states), summary=', '.join(summary))
        else:
            yield Result(state=state.worst(*states), summary=', '.join(summary))
    else:
        yield Result(
            state=state.UNKNOWN,
            summary='Received no data for this job from any of the nodes',
        )


register.check_plugin(
    name='job',
    service_name='Job %s',
    discovery_function=discover_job,
    check_default_parameters={
        "age": (0, 0)  # disabled as default
    },
    check_ruleset_name="job",
    check_function=check_job,
    cluster_check_function=cluster_check_job,
)
