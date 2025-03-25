#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.jenkins.agent_based.jenkins_queue as jq
from cmk.agent_based.v2 import Metric, Result, Service, State

TEST_TIMEZONE = ZoneInfo("CET")
TEST_TIME_2019 = datetime.datetime(2019, 8, 27, 13, 15, tzinfo=TEST_TIMEZONE)
TEST_TIME_2024 = datetime.datetime(2024, 3, 5, 19, 22, 25, tzinfo=TEST_TIMEZONE)


@pytest.fixture(scope="module", name="section")
def _section() -> jq.JenkinsQueue:
    return jq.parse_jenkins_queue(
        [
            [
                '[{"task": {"color": "blue_anime", "_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "name": "testbuild"}, "inQueueSince": 1566892922469, "why": "Build #475 is already in progress (ETA: 23 min)", "stuck": false, "_class": "hudson.model.Queue$BlockedItem", "buildableStartMilliseconds": 1566892928443, "id": 174702, "blocked": true, "pending": false}]'
            ]
        ]
    )


def test_discovery(section: jq.JenkinsQueue) -> None:
    assert list(jq.inventory_jenkins_queue(section)) == [Service()]


def test_check_jenkins_queue(section: jq.JenkinsQueue) -> None:
    params: jq.ParamsDict = {
        "blocked": State.OK,
        "in_queue_since": ("fixed", (3600, 7200)),
        "jenkins_stuck_tasks": ("fixed", (1, 2)),
        "pending": State.OK,
        "stuck": State.CRIT,
    }

    with time_machine.travel(TEST_TIME_2019):
        assert list(jq.check_jenkins_queue(params, section)) == [
            Result(state=State.OK, summary="Queue length: 1 Tasks"),
            Metric("queue", 1),
            Result(state=State.OK, summary="Stuck: 0"),
            Metric("jenkins_stuck_tasks", 0, levels=(1, 2)),
            Result(state=State.OK, summary="Blocked: 1"),
            Metric("jenkins_blocked_tasks", 1),
            Result(state=State.OK, summary="Pending: 0"),
            Metric("jenkins_pending_tasks", 0),
            Result(
                state=State.CRIT,
                notice=(
                    "ID: 174702, Stuck: no, Blocked: yes, Pending: no, "
                    "In queue since: 2019-08-27 10:02:02 - 3 hours 12 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes), "
                    "Why kept: Build #475 is already in progress (ETA: 23 min)"
                ),
            ),
        ]


@pytest.fixture(scope="module", name="multi_task_section")
def _multi_task_section() -> jq.JenkinsQueue:
    return jq.parse_jenkins_queue(
        [
            [
                '[{"_class": "hudson.model.Queue$BuildableItem", "blocked": false, "id": 18, "inQueueSince": 1709648603185, "stuck": false, "task": {"_class": "hudson.model.FreeStyleProject", "name": "more", "color": "notbuilt"}, "why": "\\u2018Jenkins\\u2019 is reserved for jobs with matching label expression; \\u2018ubu2\\u2019 is offline; \\u2018ubu\\u2019 is offline", "buildableStartMilliseconds": 1709648603186, "pending": false}, {"_class": "hudson.model.Queue$BuildableItem", "blocked": false, "id": 17, "inQueueSince": 1709648516803, "stuck": true, "task": {"_class": "hudson.model.FreeStyleProject", "name": "asdf", "color": "blue"}, "why": "\\u2018Jenkins\\u2019 is reserved for jobs with matching label expression; \\u2018ubu2\\u2019 is offline; \\u2018ubu\\u2019 is offline", "buildableStartMilliseconds": 1709648516816, "pending": false}]'
            ]
        ]
    )


def test_check_jenkins_queue_with_multiple_tasks(multi_task_section: jq.JenkinsQueue) -> None:
    params: jq.ParamsDict = {
        "blocked": State.OK,
        "in_queue_since": ("fixed", (3600, 7200)),
        "jenkins_stuck_tasks": ("fixed", (1, 2)),
        "pending": State.OK,
        "stuck": State.CRIT,
    }

    with time_machine.travel(TEST_TIME_2024):
        assert list(jq.check_jenkins_queue(params, multi_task_section)) == [
            Result(state=State.OK, summary="Queue length: 2 Tasks"),
            Metric("queue", 2),
            Result(state=State.WARN, summary="Stuck: 1 (warn/crit at 1/2)"),
            Metric("jenkins_stuck_tasks", 1, levels=(1, 2)),
            Result(state=State.OK, summary="Blocked: 0"),
            Metric("jenkins_blocked_tasks", 0),
            Result(state=State.OK, summary="Pending: 0"),
            Metric("jenkins_pending_tasks", 0),
            Result(
                state=State.CRIT,
                summary=(
                    "ID: 17, Stuck: yes, Blocked: no, Pending: no, "
                    "In queue since: 2024-03-05 15:21:56 - 4 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes), "
                    "Why kept: ‘Jenkins’ is reserved for jobs with matching label expression; ‘ubu2’ is offline; ‘ubu’ is offline"
                ),
            ),
            Result(
                state=State.CRIT,
                summary=(
                    "ID: 18, Stuck: no, Blocked: no, Pending: no, "
                    "In queue since: 2024-03-05 15:23:23 - 3 hours 59 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes), "
                    "Why kept: ‘Jenkins’ is reserved for jobs with matching label expression; ‘ubu2’ is offline; ‘ubu’ is offline"
                ),
            ),
        ]
