#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Iterator, Mapping
from typing import Final, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
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


class CheckParameters(TypedDict):
    age: tuple[int, int] | None
    exit_code_to_state_map: list[tuple[int, int]]


_METRIC_TRANSLATION: Final = {
    "real": "real_time",
    "user": "user_time",
    "sys": "system_time",
    # On AIX, /usr/bin/time localises its labels through LC_MESSAGES (catgets),
    # so non-POSIX locales can emit "Real"/"User"/"System". The legacy IBM
    # en_US.ISO8859-1 catalog is the known case where this happens.
    "Real": "real_time",
    "User": "user_time",
    "System": "system_time",
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


def _split_job_tables(string_table: StringTable) -> Iterator[tuple[list[str], StringTable]]:
    """Split the section into one (header, body) pair per mk-job file.

    Bodies may be empty: mk-job creates the file before it has anything to write
    into it, so the agent can pick it up while it is still empty.
    """
    header: list[str] = []
    buffer: StringTable = []
    for line in string_table:
        if line[0] == "==>" and line[-1] == "<==":
            if header:
                yield header, buffer
            header = line
            # A new list instead of clearing the old one: our caller holds on to
            # every buffer we have yielded so far.
            buffer = []
            continue

        buffer.append(line)

    if header:
        yield header, buffer


def _is_zombie(body: StringTable) -> bool:
    """Tell a running job apart from a leftover ".<pid>running" file.

    mk-job copies the file of a running job right after writing its start time,
    and appends everything else to the completed file only. So anything but that
    single line means the job is not running any more - it was killed, or we are
    looking at a partially written file.

    NOTE: zombie jobs and empty files are most likely due to non-atomic file
    operations, which are addressed in werk 15450. So, when mk-job agent plugins
    that do not include this werk are no longer supported (haha), code to handle
    it could be removed.
    """
    return len(body) != 1 or body[0][0] != "start_time"


def _get_jobname_and_running_state(header: list[str], body: StringTable) -> tuple[str, str]:
    """determine whether the job is running. some jobs are flagged as
    running jobs, but are in fact not (i.e. they are pseudo running), for
    example killed jobs.
    returns a tuple containing the job name without the 'running' postfix
    (if applicable) and one of three possible running states:
        - 'running'
        - 'not_running'
        - 'pseudo_running'
    """
    jobname = " ".join(header[1:-1])

    if not jobname.endswith("running"):
        return jobname, "not_running"

    jobname = jobname.rsplit(".", 1)[0]

    return jobname, "pseudo_running" if _is_zombie(body) else "running"


def parse_job(string_table: StringTable) -> Section:
    parsed: Section = {}
    for header, body in _split_job_tables(string_table):
        jobname, running_state = _get_jobname_and_running_state(header, body)
        running = running_state == "running"

        if running_state == "pseudo_running":
            # A leftover ".<pid>running" file of a job that is not running any
            # more. Its contents do not describe the last completed run: the
            # exit code written by /usr/bin/time is 0 for a job that died from
            # a signal, for example. So we go by the completed file instead.
            continue

        metrics: Metrics = {}
        job_stats: Job = {
            "running": running,
            "metrics": metrics,
        }
        job = parsed.setdefault(jobname, job_stats)
        # the setdefault means: the first job wins. so if we see a running job first, and a
        # stopped afterwards, the job is running.
        # but if we se a stopped job first and then a running one, then its still reported as
        # stopped, which is not correct.
        # running should overwrite stopped, but stopped should not overwrite running:
        if job_stats["running"] is True:
            job["running"] = True

        for line in body:
            if len(line) != 2:
                continue
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

    return parsed


agent_section_job = AgentSection(
    name="job",
    parse_function=parse_job,
)


def discover_job(section: Section) -> DiscoveryResult:
    for jobname, _job in section.items():
        yield Service(item=jobname)


_METRIC_SPECS: Mapping[str, tuple[str, Callable[[float | int], str]]] = {
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
    yield from check_levels(
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

    # Werk 7477: the age levels apply to the job that has been running the longest.
    used_start_time = min(job["running_start_time"]) if currently_running else job["start_time"]
    if (age := now - used_start_time) >= 0:
        yield from check_levels(
            age,
            metric_name="job_age",
            label=f"Job age{currently_running}",
            # In pre-2.0 versions of this check plug-in, we had
            # check_default_parameters={"age": (0, 0)}
            # However, these levels were only applied if they were not zero. We still need to keep this
            # check because many old autocheck files still have
            # 'parameters': {'age': (0, 0)}
            # which must not result in actually applying these levels.
            levels_upper=(
                ("fixed", age_levels) if age_levels is not None and age_levels != (0, 0) else None
            ),
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
    params: CheckParameters,
    section: Section,
) -> CheckResult:
    job = section.get(item)
    if job is None:
        return

    if job.get("exit_code") is None or not ("start_time" in job or "running_start_time" in job):
        yield Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
        )
        return

    yield from _process_job_stats(
        job,
        params["age"],
        {k: State(v) for k, v in params["exit_code_to_state_map"]},
        time.time(),
    )


check_plugin_job = CheckPlugin(
    name="job",
    service_name="Job %s",
    discovery_function=discover_job,
    check_default_parameters={"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
    check_ruleset_name="job",
    check_function=check_job,
)
