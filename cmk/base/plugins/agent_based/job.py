#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import (
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    TypedDict,
    Tuple,
)
from .agent_based_api.v1 import (
    check_levels,
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

Metrics = Dict[str, float]


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


def _job_parse_key_values(line: List[str]) -> Tuple[str, float]:
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


def discover_job(section: Section) -> type_defs.DiscoveryResult:
    for jobname, job in section.items():
        if not job["running"]:
            yield Service(item=jobname)


_METRIC_SPECS: Mapping[str, Tuple[str, Callable]] = {
    'real_time': ('Real time', render.timespan),
    'user_time': ('User time', render.timespan),
    'system_time': ('System time', render.timespan),
    'reads': ('Filesystem reads', str),
    'writes': ('Filesystem writes', str),
    'max_res_bytes': ('Max. memory', render.bytes),
    'avg_mem_bytes': ('Avg. memory', render.bytes),
    'vol_context_switches': ('Vol. context switches', str),
    'invol_context_switches': ('Invol. context switches', str),
}


def _check_job_levels(job: Job, metric: str, notice_only: bool = True):
    label, render_func = _METRIC_SPECS[metric]
    yield from check_levels(
        job['metrics'][metric],
        metric_name=metric,
        label=label,
        render_func=render_func,
        notice_only=notice_only,
    )


def _process_job_stats(
    job: Job,
    age_levels: Optional[Tuple[int, int]],
    exit_code_to_state_map: Dict[int, state],
) -> type_defs.CheckResult:

    yield Result(
        state=exit_code_to_state_map.get(job['exit_code'], state.CRIT),
        summary=f"Latest exit code: {job['exit_code']}",
    )

    metrics_to_output = set(job['metrics'])

    if 'real_time' in metrics_to_output:
        metrics_to_output.remove('real_time')
        yield from _check_job_levels(job, 'real_time', notice_only=False)

    currently_running = " (currently running)" if 'running_start_time' in job else ""
    # use start time of oldest running job, if any.
    if currently_running:
        start_times = job['running_start_time']
        count = len(start_times)
        yield Result(
            state=state.OK,
            notice="%d job%s currently running, started at %s" % (
                count,
                " is" if count == 1 else "s are",
                ', '.join((render.datetime(t) for t in start_times)),
            ),
        )
    else:
        yield Result(
            state=state.OK,
            notice="Latest job started at %s" % render.datetime(job['start_time']),
        )
        yield Metric('start_time', job['start_time'])

    used_start_time = max(job['running_start_time']) if currently_running else job['start_time']
    yield from check_levels(
        time.time() - used_start_time,
        label=f"Job age{currently_running}",
        # In pre-2.0 versions of this check plugin, we had
        # check_default_parameters={"age": (0, 0)}
        # However, these levels were only applied if they were not zero. We still need to keep this
        # check because many old autocheck files still have
        # 'parameters': {'age': (0, 0)}
        # which must not result in actually applying these levels.
        levels_upper=age_levels if age_levels != (0, 0) else None,
        render_func=render.timespan,
    )

    for metric in sorted(metrics_to_output):
        yield from _check_job_levels(job, metric)


def check_job(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:

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
        params.get('age'),
        {
            0: state.OK,
            **{k: state(v) for k, v in params.get('exit_code_to_state_map', [])}
        },
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
) -> type_defs.CheckResult:
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
    check_default_parameters={},
    check_ruleset_name="job",
    check_function=check_job,
    cluster_check_function=cluster_check_job,
)
