#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import auto, Enum
from typing import Final, Self

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
from cmk.plugins.job.lib import CheckParameters, ExitCodeState
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

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
    # On AIX, /usr/bin/time localises its labels through LC_MESSAGES (catgets),
    # so non-POSIX locales can emit "Real"/"User"/"System". The legacy IBM
    # en_US.ISO8859-1 catalog is the known case where this happens.
    "Real": "real_time",
    "User": "user_time",
    "System": "system_time",
}

# mk-job names the file of a running job "<jobname>.<pid>running". Old versions
# omitted the pid, so it may be empty.
_JOB_HEADER: Final = re.compile(r"(?P<jobname>.+?)(?P<running>\.(?P<pid>\d*)running)?")


class RunState(Enum):
    RUNNING = auto()
    COMPLETED = auto()


def _as[T](_type: Callable[[str], T], value: str | None) -> T | None:
    """Apply _type to value, mapping anything unparsable to None.

    Every field of an mk-job file may be missing or garbled: /usr/bin/time may
    not be installed at all, and on AIX/Solaris mk-job merges the job's own
    stderr into the file (see agents/mk-job.aix).
    """
    if value is None:
        return None
    try:
        return _type(value)
    except TypeError, ValueError:
        return None


@dataclass
class Metrics:
    real_time: float | None
    user_time: float | None
    system_time: float | None
    reads: int | None
    writes: int | None
    max_res_bytes: int | None
    avg_mem_bytes: int | None
    invol_context_switches: int | None
    vol_context_switches: int | None

    @classmethod
    def from_dict(cls, values: Mapping[str, str]) -> Self:
        translated = {
            # Some locales use a comma as the decimal marker.
            _METRIC_TRANSLATION.get(name, name): value.replace(",", ".")
            for name, value in values.items()
        }
        max_res_kbytes = _as(int, translated.get("max_res_kbytes"))
        avg_mem_kbytes = _as(int, translated.get("avg_mem_kbytes"))
        return cls(
            real_time=_as(_job_parse_real_time, translated.get("real_time")),
            user_time=_as(float, translated.get("user_time")),
            system_time=_as(float, translated.get("system_time")),
            reads=_as(int, translated.get("reads")),
            writes=_as(int, translated.get("writes")),
            max_res_bytes=max_res_kbytes * 1000 if max_res_kbytes is not None else None,
            avg_mem_bytes=avg_mem_kbytes * 1000 if avg_mem_kbytes is not None else None,
            invol_context_switches=_as(int, translated.get("invol_context_switches")),
            vol_context_switches=_as(int, translated.get("vol_context_switches")),
        )


@dataclass
class RunningJob:
    name: str
    pid: int | None
    # A running file without a usable start time becomes an UndatedRunningFile
    # instead, see parse_job.
    start_time: float


@dataclass
class CompletedJob:
    name: str
    start_time: float | None
    exit_code: int | None
    metrics: Metrics


@dataclass
class UndatedRunningFile:
    """A ".<pid>running" file whose start time we cannot read.

    mk-job versions shipped with Checkmk 2.4.0 and older determine the start time
    with perl and write an empty one if perl is not installed. The job may well be
    running; there is just no telling since when, so there is nothing to report
    about it but the fact that the file is there.
    """

    name: str
    pid: int | None


Job = RunningJob | CompletedJob | UndatedRunningFile
Section = Mapping[str, Sequence[Job]]


def _job_parse_real_time(s: str) -> float:
    parts = s.split(":")
    min_sec, hour_sec = 0.0, 0.0
    if len(parts) == 3:
        hour_sec = int(parts[0]) * 60 * 60
    if len(parts) >= 2:
        min_sec = int(parts[-2]) * 60
    return float(parts[-1]) + min_sec + hour_sec


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


def _parse_header(header: list[str]) -> tuple[str, RunState, int | None] | None:
    """Return job name, run state and pid, or None if there is no job name."""
    if (match := _JOB_HEADER.fullmatch(" ".join(header[1:-1]))) is None:
        return None

    if match["running"] is None:
        return match["jobname"], RunState.COMPLETED, None

    return match["jobname"], RunState.RUNNING, _as(int, match["pid"])


def parse_job(string_table: StringTable) -> Section:
    section: dict[str, list[Job]] = {}
    for header, body in _split_job_tables(string_table):
        if (parsed_header := _parse_header(header)) is None:
            continue
        jobname, state, pid = parsed_header

        fields = {line[0]: " ".join(line[1:]) for line in body}
        start_time = _as(float, fields.pop("start_time", None))

        if state is RunState.RUNNING:
            section.setdefault(jobname, []).append(
                RunningJob(name=jobname, pid=pid, start_time=start_time)
                if start_time is not None
                else UndatedRunningFile(name=jobname, pid=pid)
            )
            continue

        section.setdefault(jobname, []).append(
            CompletedJob(
                name=jobname,
                start_time=start_time,
                exit_code=_as(int, fields.pop("exit_code", None)),
                metrics=Metrics.from_dict(fields),
            )
        )

    return section


agent_section_job = AgentSection(
    name="job",
    parse_function=parse_job,
)


def discover_job(section: Section) -> DiscoveryResult:
    for jobname in section:
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


def _check_completed_job(
    exit_code: int,
    metrics: Metrics,
    exit_code_to_state_map: Mapping[int, State],
) -> CheckResult:
    yield Result(
        state=exit_code_to_state_map.get(exit_code, State.CRIT),
        summary=f"Latest exit code: {exit_code}",
    )
    for name, value in asdict(metrics).items():
        if value is None:
            continue
        label, render_func = _METRIC_SPECS[name]
        yield from check_levels(
            value=value,
            metric_name=name,
            label=label,
            render_func=render_func,
            notice_only=name != "real_time",
            boundaries=(0, None),
        )


def _check_job_age(
    age: float,
    currently_running: bool,
    age_levels: SimpleLevelsConfigModel[float],
) -> CheckResult:
    if age < 0:
        yield Result(
            state=State.OK,
            summary=(
                f"Job age appears to be {render.timespan(-age)}"
                " in the future (check your system time)"
            ),
        )
        return

    yield from check_levels(
        value=age,
        metric_name="job_age",
        label=f"Job age{' (currently running)' if currently_running else ''}",
        levels_upper=age_levels,
        render_func=render.timespan,
        boundaries=(0, None),
    )


def check_job(
    item: str,
    params: CheckParameters,
    section: Section,
) -> CheckResult:
    if (jobs := section.get(item)) is None:
        return

    running_jobs = [job for job in jobs if isinstance(job, RunningJob)]
    completed_job = next((job for job in jobs if isinstance(job, CompletedJob)), None)

    # Report the files we cannot date, but keep going: whatever we do know about this
    # job comes from the other files.
    if undated := [job for job in jobs if isinstance(job, UndatedRunningFile)]:
        count = len(undated)
        pids = ", ".join(str(file.pid) for file in undated if file.pid is not None)
        yield Result(
            state=State.WARN,
            summary=(
                f"{count} running file{'' if count == 1 else 's'} without a usable start"
                f" time{f' (PID {pids})' if pids else ''}"
            ),
            details="To fix this start time issue, please update the agent or install perl on the host",
        )

    # The exit code comes from the completed job, so without one we cannot say
    # anything about the outcome.
    if completed_job is not None:
        if completed_job.exit_code is None:
            # Werk 15450 made mk-job assemble this file under $TMPDIR and move it into place, so
            # that it is "either present and complete, or absent altogether". That holds while the
            # move is a rename. With $TMPDIR on another filesystem it is a copy to the final name
            # instead - no temporary name, no rename - and a copy that fails or is interrupted
            # leaves the file truncated for good, with the exit code, written last, missing. So
            # this case survives the agents that werk 15450 shipped with: it takes a filesystem
            # layout, not an old plugin, and it does not clear up by itself.
            yield Result(
                state=State.UNKNOWN,
                summary="Got incomplete information for this job",
                details="No exit code for the last completed run - its file is probably truncated.",
            )
            return
        yield from _check_completed_job(
            completed_job.exit_code,
            completed_job.metrics,
            {
                entry["exit_code"]: State(entry["state"])
                for entry in params["exit_code_to_state_map"]
            },
        )
    elif not running_jobs:
        # A job that has not completed yet has no exit code, but as long as it is
        # running there is something to report. Without either, there is not.
        yield Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
            details="No file of a completed run - this job has probably not finished one yet, or its file is gone.",
        )
        return

    if running_jobs:
        count = len(running_jobs)
        yield Result(
            state=State.OK,
            notice=(
                f"{count} job{' is' if count == 1 else 's are'} currently running, started at"
                f" {', '.join(render.datetime(job.start_time) for job in running_jobs)}"
            ),
        )
        # Werk 7477: the age levels apply to the job that has been running the longest.
        start_time = min(job.start_time for job in running_jobs)
    elif completed_job is not None and completed_job.start_time is not None:
        yield Result(
            state=State.OK,
            notice=f"Latest job started at {render.datetime(completed_job.start_time)}",
        )
        start_time = completed_job.start_time
    else:
        # We reported the outcome of the completed job above; without a start time for
        # it, and with nothing running, there is no job age to go with it.
        yield Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
            details="No start time for the last completed run - probably no perl on the monitored host.",
        )
        return

    yield from _check_job_age(time.time() - start_time, bool(running_jobs), params["age"])


check_plugin_job = CheckPlugin(
    name="job",
    service_name="Job %s",
    discovery_function=discover_job,
    check_default_parameters=CheckParameters(
        age=("no_levels", None),
        exit_code_to_state_map=[ExitCodeState(exit_code=0, state=0)],
    ),
    check_ruleset_name="job",
    check_function=check_job,
)
