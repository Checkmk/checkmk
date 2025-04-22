#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jenkins_queue>>>
# [[u'[{"task": {"color": "blue_anime", "_class":
# "org.jenkinsci.plugins.workflow.job.WorkflowJob", "name": "testbuild"},
# "inQueueSince": 1566823138742, "why": "Build #471 is already in progress
# (ETA: 38 min)", "stuck": false, "_class": "hudson.model.Queue$BlockedItem",
# "buildableStartMilliseconds": 1566823144626, "id": 174032, "blocked":
# true}]']]

import json
import time
from typing import Any, NamedTuple, NotRequired, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)

from .lib import render_integer


class ParamsDict(TypedDict):
    queue_length: NotRequired[FixedLevelsT]
    in_queue_since: FixedLevelsT
    stuck: State
    blocked: State
    pending: State
    jenkins_stuck_tasks: FixedLevelsT


class JenkinsTask(TypedDict):
    id: int
    stuck: bool
    blocked: bool
    pending: NotRequired[bool]
    inQueueSince: int
    why: str


class ProcessedTask(NamedTuple):
    state: State
    description: str


JenkinsQueue = list[JenkinsTask]

MAP_QUEUE_STATES = {
    True: "yes",
    False: "no",
}


def parse_jenkins_queue(string_table: StringTable) -> JenkinsQueue:
    parsed = []

    for line in string_table:
        parsed.extend(json.loads(line[0]))

    return parsed


def inventory_jenkins_queue(section: JenkinsQueue) -> DiscoveryResult:
    yield Service()


def check_jenkins_queue(params: ParamsDict, section: JenkinsQueue) -> CheckResult:
    yield from _check_jenkins_queue(params, section)


def _check_jenkins_queue(
    params: ParamsDict, section: JenkinsQueue, now: int | float | None = None
) -> CheckResult:
    yield from check_levels(
        len(section),
        metric_name="queue",
        levels_upper=params.get("queue_length"),
        render_func=lambda n: f"{n} Tasks",
        label="Queue length",
    )

    if now is None:
        now = time.time()
    assert isinstance(now, float | int)

    def task_order_helper(task: JenkinsTask) -> tuple[bool, bool, int]:
        is_stuck = task["stuck"]
        is_blocked = task["blocked"]
        in_queue_since = task["inQueueSince"]

        return (is_stuck, is_blocked, -in_queue_since)

    queue_state = {
        "stuck_tasks": 0,
        "blocked_tasks": 0,
        "pending_tasks": 0,
    }

    # Sort tasks by their state of stuck, blocked and duration in queue.
    # Go through every task in the queue and collect details about their state.
    # The details will be shown after the a general queue summary.
    queue_details = [
        process_task_in_queue(task, params, queue_state, now)
        for task in sorted(section, key=task_order_helper, reverse=True)
    ]

    # Generate an overview of stuck, blocked and pending tasks
    for metric_name, infotext in [
        ("stuck_tasks", "Stuck"),
        ("blocked_tasks", "Blocked"),
        ("pending_tasks", "Pending"),
    ]:
        amount = queue_state[metric_name]

        jenkins_value = f"jenkins_{metric_name}"

        # A better type would be FixedLevelsT | None but mypy does not seem to be able to
        # handle the indirect creation of the key and isn't able to properly detect the
        # used types.
        task_levels: Any = params.get(jenkins_value)

        yield from check_levels(
            amount,
            metric_name=jenkins_value,
            levels_upper=task_levels,
            render_func=render_integer,
            label=infotext,
        )

    # Output detailed information about tasks in the queue.
    # Using notice here will lead to a job being visible in the summary if things go wrong.
    for task in queue_details:
        yield Result(
            state=task.state,
            notice=task.description,
        )


def process_task_in_queue(
    task: JenkinsTask, params: ParamsDict, queue_state: dict[str, int], now: float | int
) -> ProcessedTask:
    stuck_state = State.OK
    if task["stuck"]:
        queue_state["stuck_tasks"] += 1
        stuck_state = params["stuck"]

    blocked_state = State.OK
    if task["blocked"]:
        queue_state["blocked_tasks"] += 1
        blocked_state = params["blocked"]

    is_stuck = task["stuck"]
    is_blocked = task["blocked"]

    task_details = [
        f"ID: {task['id']}",
        f"Stuck: {MAP_QUEUE_STATES[is_stuck]}",
        f"Blocked: {MAP_QUEUE_STATES[is_blocked]}",
    ]

    pending_state = State.OK
    # pending can be missing
    if (task_pending := task.get("pending")) is not None:
        if task_pending:
            queue_state["pending_tasks"] += 1
        pending_state = params["pending"]
        task_details.append(f"Pending: {MAP_QUEUE_STATES[task_pending]}")

    task_in_queue_since = task["inQueueSince"]
    timestamp_in_queue = task_in_queue_since / 1000
    since = now - timestamp_in_queue

    queued_duration_result, *_metrics = check_levels(
        since,
        levels_upper=params["in_queue_since"],
        render_func=render.timespan,
    )
    assert isinstance(queued_duration_result, Result)
    task_details.append(
        f"In queue since: {render.datetime(timestamp_in_queue)} - {queued_duration_result.summary}"
    )
    task_details.append(f"Why kept: {task['why']}")

    task_state = State.worst(
        queued_duration_result.state, stuck_state, blocked_state, pending_state
    )

    return ProcessedTask(state=task_state, description=", ".join(task_details))


agent_section_jenkins_queue = AgentSection(
    name="jenkins_queue",
    parse_function=parse_jenkins_queue,
)

check_plugin_jenkins_queue = CheckPlugin(
    name="jenkins_queue",
    service_name="Jenkins Queue",
    discovery_function=inventory_jenkins_queue,
    check_function=check_jenkins_queue,
    check_ruleset_name="jenkins_queue",
    check_default_parameters={
        "in_queue_since": ("fixed", (3600, 7200)),
        "stuck": State.CRIT.value,
        "blocked": State.OK.value,
        "pending": State.OK.value,
        "jenkins_stuck_tasks": ("fixed", (1, 2)),
    },
)
