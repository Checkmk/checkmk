#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class Job:
    type_: str
    last_state: str
    last_result: str
    creation_time: str
    end_time: str


@dataclass(frozen=True, kw_only=True)
class Workload:
    name: str
    last_state: str
    last_result: str
    creation_time: str
    end_time: str


@dataclass(frozen=True, kw_only=True)
class PolicyWorkloads:
    workloads: Sequence[Workload]
    error: str | None


JobsSection = Mapping[str, Job | None]
# Protected computers of policies managed by the agent, by policy name. An error for
# all policies is stored under ALL_POLICIES.
WorkloadsSection = Mapping[str, PolicyWorkloads]
ALL_POLICIES = "*"


def discovery_veeam_jobs(
    section_veeam_jobs: JobsSection | None,
    section_veeam_agent_policy_workloads: WorkloadsSection | None,  # noqa: ARG001
) -> DiscoveryResult:
    yield from (Service(item=item) for item in section_veeam_jobs or {})


_RUNNING_STATES = ("Starting", "Working", "Postprocessing")
_NOT_RUNNING_STATES = ("Idle", "Stopped", "Suspended")


def monitoring_state(last_state: str, last_result: str) -> State:
    match last_result:
        case "None":
            if last_state in _RUNNING_STATES:
                # If result is absent and the job is still running, we cannot check the result yet.
                # We try to get previous result from the last run.
                raise IgnoreResultsError("Data not present at the moment")
            if last_state in _NOT_RUNNING_STATES:
                # The job exists and was queried successfully, it simply has no
                # execution history yet: its first run is still pending.
                return State.OK
            return State.UNKNOWN
        case "Success":
            return State.OK
        case "Failed":
            return State.CRIT
        case "Warning":
            return State.WARN
        case _:
            return State.UNKNOWN


def check_veeam_jobs(
    item: str,
    section_veeam_jobs: JobsSection | None,
    section_veeam_agent_policy_workloads: WorkloadsSection | None,
) -> CheckResult:
    if section_veeam_jobs is None or (job := section_veeam_jobs.get(item)) is None:
        return

    yield Result(
        state=monitoring_state(job.last_state, job.last_result),
        summary=f"State: {job.last_state}, Result: {job.last_result}",
    )
    if job.creation_time != "":
        yield Result(state=State.OK, summary=f"Creation time: {job.creation_time}")
    if job.end_time != "":
        yield Result(state=State.OK, summary=f"End time: {job.end_time}")
    yield Result(state=State.OK, summary=f"Type: {job.type_}")

    workloads_section = section_veeam_agent_policy_workloads or {}
    if job.type_ == "EpAgentPolicy" and (all_policies := workloads_section.get(ALL_POLICIES)):
        yield from _check_error(all_policies.error)
    if (policy := workloads_section.get(item)) is not None:
        yield from _check_error(policy.error)
        yield from _check_workloads(policy.workloads)


def _check_error(error: str | None) -> CheckResult:
    if error is not None:
        yield Result(
            state=State.UNKNOWN, summary=f"Could not determine the protected computers: {error}"
        )


_MAX_LISTED_PROBLEMS = 3
_PROBLEM_LABELS = {
    State.CRIT: "failed backups",
    State.WARN: "backup warnings",
    State.UNKNOWN: "unknown backup results",
}


def _describe(workload: Workload) -> str:
    if workload.end_time:
        return f"{workload.name}: {workload.last_result} (ended {workload.end_time})"
    return f"{workload.name}: {workload.last_result}"


def _check_workloads(workloads: Sequence[Workload]) -> CheckResult:
    if not workloads:
        return

    by_state: dict[State, list[Workload]] = {}
    without_backup = []
    for workload in workloads:
        if workload.last_state == "None":
            without_backup.append(workload.name)
            continue
        try:
            state = monitoring_state(workload.last_state, workload.last_result)
        except IgnoreResultsError:
            # The agent only sends finished backups, a running one has no result to report
            continue
        by_state.setdefault(state, []).append(workload)

    problems = [w for state, ws in by_state.items() if state is not State.OK for w in ws]
    for state, label in _PROBLEM_LABELS.items():
        if not (affected := by_state.get(state)):
            continue
        if len(problems) <= _MAX_LISTED_PROBLEMS:
            yield from (Result(state=state, summary=_describe(w)) for w in affected)
        else:
            yield Result(
                state=state,
                summary=f"Protected computers with {label}: {len(affected)}",
                details="\n".join(_describe(w) for w in affected),
            )

    if healthy := by_state.get(State.OK):
        yield Result(
            state=State.OK,
            notice=f"Protected computers without problems: {len(healthy)}",
            details="\n".join(_describe(w) for w in healthy),
        )

    if without_backup:
        yield Result(
            state=State.OK,
            notice=f"Protected computers without a finished backup yet: {len(without_backup)}",
            details="\n".join(without_backup),
        )


def parse_veeam_jobs(string_table: StringTable) -> Mapping[str, Job | None]:
    section: dict[str, Job | None] = {}
    for line in string_table:
        if len(line) < 2:
            section[line[0]] = None
        else:
            # If end_time/creation_time are empty strings, then tab seperators are simply discarded,
            # thus the resulting string_table line has 4 or 5 elements, despite being valid.
            # We reinsert the missing emtpy str by hand.
            type_, last_state, last_result, creation_time, end_time = [*line, "", ""][1:6]
            section[line[0]] = Job(
                type_=type_,
                last_state=last_state,
                last_result=last_result,
                creation_time=creation_time,
                end_time=end_time,
            )
    return section


agent_section_veeam_jobs = AgentSection(
    name="veeam_jobs",
    parse_function=parse_veeam_jobs,
)


def parse_veeam_agent_policy_workloads(string_table: StringTable) -> WorkloadsSection:
    workloads: dict[str, list[Workload]] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match line:
            case ["error", policy, *message]:
                errors[policy] = " ".join(message)
            case ["computer", policy, name, last_state, last_result, *times]:
                creation_time, end_time = [*times, "", ""][:2]
                workloads.setdefault(policy, []).append(
                    Workload(
                        name=name,
                        last_state=last_state,
                        last_result=last_result,
                        creation_time=creation_time,
                        end_time=end_time,
                    )
                )
            case _:
                continue
    return {
        policy: PolicyWorkloads(workloads=workloads.get(policy, []), error=errors.get(policy))
        for policy in workloads.keys() | errors.keys()
    }


agent_section_veeam_agent_policy_workloads = AgentSection(
    name="veeam_agent_policy_workloads",
    parse_function=parse_veeam_agent_policy_workloads,
)

check_plugin_veeam_jobs = CheckPlugin(
    name="veeam_jobs",
    sections=["veeam_jobs", "veeam_agent_policy_workloads"],
    service_name="VEEAM Job %s",
    discovery_function=discovery_veeam_jobs,
    check_function=check_veeam_jobs,
)
