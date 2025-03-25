#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping
from typing import Any, Final, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

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

_METRIC_TRANSLATION: Final = {
    "real": "real_time",
    "user": "user_time",
    "sys": "system_time",
}

Metrics = dict[str, float]


class Job(TypedDict, total=False):
    running: bool
    exit_code: int
    start_time: float
    running_start_time: list[int]
    metrics: Metrics


Section = dict[str, Job]


def _job_parse_real_time(s: str) -> float:
    parts = s.split(":")
    min_sec, hour_sec = 0, 0
    if len(parts) == 3:
        hour_sec = int(parts[0]) * 60 * 60
    if len(parts) >= 2:
        min_sec = int(parts[-2]) * 60
    return float(parts[-1]) + min_sec + hour_sec


def _job_parse_metrics(line: list[str]) -> tuple[str, float]:
    name, value = line
    name = _METRIC_TRANSLATION.get(name, name)
    value = value.replace(",", ".")
    if name == "real_time":
        return name, _job_parse_real_time(value)
    if name in ("user_time", "system_time"):
        return name, float(value)
    if name in ("max_res_kbytes", "avg_mem_kbytes"):
        return name.replace("kbytes", "bytes"), int(value) * 1000
    return name, int(value)


def _get_jobname_and_running_state(
    string_table: StringTable,
) -> tuple[str, str]:
    """determine whether the job is running. some jobs are flagged as
    running jobs, but are in fact not (i.e. they are pseudo running), for
    example killed jobs.
    returns a tuple containing the job name without the 'running' postfix
    (if applicable) and one of three possible running states:
        - 'running'
        - 'not_running'
        - 'pseudo_running'
    """
    jobname = " ".join(string_table[0][1:-1])

    if not jobname.endswith("running"):
        return jobname, "not_running"

    jobname = jobname.rsplit(".", 1)[0]

    # NOTE: pseudo_running jobs and empty files are most likely due to non-atomic
    # file operations, which are addressed in werk 15450, so when mk-job agent
    # plugins that do not include this werk are no longer supported (haha),
    # code to handle it could be removed

    # real running jobs ...
    # ... have the start time defined ...
    if len(string_table) < 2 or string_table[1][0] != "start_time":
        return jobname, "pseudo_running"

    # ... and then the subsection ends
    if len(string_table) > 2 and string_table[2][0] != "==>":
        return jobname, "pseudo_running"

    return jobname, "running"


def parse_job(string_table: StringTable) -> Section:
    parsed: Section = {}
    pseudo_running_jobs: Section = {}  # contains jobs that are flagged as running but are not, e.g. killed jobs
    job: Job = {}
    for idx, line in enumerate(string_table):
        if line[0] == "==>" and line[-1] == "<==":
            jobname, running_state = _get_jobname_and_running_state(string_table[idx:])
            running = running_state == "running"

            metrics: Metrics = {}
            job_stats: Job = {
                "running": running,
                "metrics": metrics,
            }
            if running_state == "pseudo_running":
                job = pseudo_running_jobs.setdefault(jobname, job_stats)
                continue

            job = parsed.setdefault(jobname, job_stats)
            # the setdefault means: the first job wins. so if we see a running job first, and a
            # stopped afterwards, the job is running.
            # but if we se a stopped job first and then a running one, then its still reported as
            # stopped, which is not correct.
            # running should overwrite stopped, but stopped should not overwrite running:
            if job_stats["running"] is True:
                job["running"] = True

        elif job and len(line) == 2:
            name, value = _job_parse_metrics(line)
            if running:
                job.setdefault("running_start_time", []).append(int(value))
            elif name == "exit_code":
                job["exit_code"] = int(value)
            elif name == "start_time":
                job["start_time"] = value
            else:
                assert name in _METRIC_SPECS
                metrics[name] = value

    for jobname, job_stats in pseudo_running_jobs.items():
        # NOTE: pseudo_running jobs and empty files are most likely due to non-atomic
        # file operations, which are addressed in werk 15450, so when mk-job agent
        # plugins that do not include this werk are no longer supported (haha),
        # code to handle it could be removed
        if job_stats.get("start_time", -1) > parsed.get(jobname, {}).get("start_time", 0):
            parsed[jobname] = job_stats

    return parsed


agent_section_job = AgentSection(
    name="job",
    parse_function=parse_job,
)


def discover_job(section: Section) -> DiscoveryResult:
    for jobname, _job in section.items():
        yield Service(item=jobname)


_METRIC_SPECS: Mapping[str, tuple[str, Callable]] = {
    "real_time": ("Real time", render.timespan),
    "user_time": ("User time", render.timespan),
    "system_time": ("System time", render.timespan),
    "reads": ("Filesystem reads", str),
    "writes": ("Filesystem writes", str),
    "max_res_bytes": ("Max. memory", render.bytes),
    "avg_mem_bytes": ("Avg. memory", render.bytes),
    "vol_context_switches": ("Vol. context switches", str),
    "invol_context_switches": ("Invol. context switches", str),
}


def _check_job_levels(job: Job, metric: str, notice_only: bool = True) -> CheckResult:
    label, render_func = _METRIC_SPECS[metric]
    yield from check_levels_v1(
        job["metrics"][metric],
        metric_name=metric,
        label=label,
        render_func=render_func,
        notice_only=notice_only,
        boundaries=(0, None),
    )


def _process_job_stats(
    job: Job,
    age_levels: tuple[int, int] | None,
    exit_code_to_state_map: dict[int, State],
    now: float,
) -> CheckResult:
    yield Result(
        state=exit_code_to_state_map.get(job["exit_code"], State.CRIT),
        summary=f"Latest exit code: {job['exit_code']}",
    )

    metrics_to_output = set(job["metrics"])

    if "real_time" in metrics_to_output:
        metrics_to_output.remove("real_time")
        yield from _check_job_levels(job, "real_time", notice_only=False)

    currently_running = " (currently running)" if "running_start_time" in job else ""
    # use start time of oldest running job, if any.
    if currently_running:
        start_times = job["running_start_time"]
        count = len(start_times)
        yield Result(
            state=State.OK,
            notice="%d job%s currently running, started at %s"
            % (
                count,
                " is" if count == 1 else "s are",
                ", ".join(render.datetime(t) for t in start_times),
            ),
        )
    else:
        yield Result(
            state=State.OK,
            notice="Latest job started at %s" % render.datetime(job["start_time"]),
        )

    used_start_time = max(job["running_start_time"]) if currently_running else job["start_time"]
    if (age := now - used_start_time) >= 0:
        yield from check_levels_v1(
            age,
            metric_name="job_age",
            label=f"Job age{currently_running}",
            # In pre-2.0 versions of this check plug-in, we had
            # check_default_parameters={"age": (0, 0)}
            # However, these levels were only applied if they were not zero. We still need to keep this
            # check because many old autocheck files still have
            # 'parameters': {'age': (0, 0)}
            # which must not result in actually applying these levels.
            levels_upper=age_levels if age_levels != (0, 0) else None,
            render_func=render.timespan,
            boundaries=(0, None),
        )
    else:
        yield Result(
            state=State.OK,
            summary=(
                f"Job age appears to be {render.timespan(-age)}"
                " in the future (check your system time)"
            ),
        )

    for metric in sorted(metrics_to_output):
        yield from _check_job_levels(job, metric)


def check_job(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    job = section.get(item)
    if job is None:
        return

    if job.get("exit_code") is None:
        yield Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
        )
        return

    yield from _process_job_stats(
        job,
        params.get("age"),
        {0: State.OK, **{k: State(v) for k, v in params.get("exit_code_to_state_map", [])}},
        time.time(),
    )


_STATE_TO_STR = {
    State.OK: "OK",
    State.WARN: "WARN",
    State.CRIT: "CRIT",
    State.UNKNOWN: "UNKNOWN",
}

check_plugin_job = CheckPlugin(
    name="job",
    service_name="Job %s",
    discovery_function=discover_job,
    check_default_parameters={},
    check_ruleset_name="job",
    check_function=check_job,
)
