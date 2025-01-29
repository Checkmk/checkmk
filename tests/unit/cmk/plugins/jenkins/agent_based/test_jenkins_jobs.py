#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.jenkins.agent_based.jenkins_jobs import (
    _check_jenkins_jobs,
    check_jenkins_jobs,
    discovery_jenkins_jobs,
    parse_jenkins_jobs,
    Section,
)

TEST_TIME = 1637672400  # 2021-11-23 13:00:00


@pytest.fixture(scope="module", name="section")
def _section() -> Section:
    return parse_jenkins_jobs(
        [
            [
                '[{"_class": "com.cloudbees.hudson.plugins.folder.Folder", "displayNameOrNull": "Folder1", "name": "project", "healthReport": [{"score": 50}], "jobs": [{"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "displayNameOrNull": "Job", "name": "Job", "color": "blue", "healthReport": [{"score": 80}], "lastBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "duration": 507524, "number": 53, "result": "SUCCESS", "timestamp": 1637059997346}, "lastSuccessfulBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "timestamp": 1637059997346}}, {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "displayNameOrNull": "Job 1", "name": "Job1", "color": "notbuilt", "healthReport": [], "lastBuild": "null"}, {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "displayNameOrNull": "Job 2", "name": "Job2", "color": "blue", "healthReport": [{"score": 50}], "lastBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "duration": 212036, "number": 30, "result": "SUCCESS", "timestamp": 1637062224758}, "lastSuccessfulBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "timestamp": 1637062224758}}, {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "displayNameOrNull": "Job 3", "name": "Job3", "color": "blue", "healthReport": [{"score": 100}], "lastBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "duration": 193715, "number": 26, "result": "FAILURE", "timestamp": 1637062443432}, "lastSuccessfulBuild": {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun", "timestamp": 1637062443432}}]}]'
            ]
        ]
    )


def test_discovery_jenkins_org_folder():
    section = parse_jenkins_jobs(
        [
            [
                '[{"_class":"jenkins.branch.OrganizationFolder","displayNameOrNull":null,"name":"gitea","healthReport":[],"jobs":[]},{"_class":"com.cloudbees.hudson.plugins.folder.Folder","displayNameOrNull":null,"name":"Powershell","healthReport":[],"jobs":[{"_class":"hudson.model.FreeStyleProject","displayNameOrNull":null,"name":"Add-Laptops-Group","color":"red","healthReport":[{"score":40}],"lastBuild":{"_class":"hudson.model.FreeStyleBuild","duration":1189,"number":219,"result":"FAILURE","timestamp":1643800688467},"lastSuccessfulBuild":{"_class":"hudson.model.FreeStyleBuild","timestamp":1643800687047}}]}]'
            ]
        ]
    )

    assert list(discovery_jenkins_jobs(section)) == [
        Service(item="Powershell/Add-Laptops-Group"),
    ]


def test_discovery(section: Section) -> None:
    assert list(discovery_jenkins_jobs(section)) == [
        Service(item="project/Job"),
        Service(item="project/Job1"),
        Service(item="project/Job2"),
        Service(item="project/Job3"),
    ]


def test_check_job_item(section: Section) -> None:
    """Successfull job"""
    assert list(_check_jenkins_jobs("project/Job", {}, section, now=TEST_TIME)) == [
        Result(state=State.OK, summary="Display name: Job"),
        Result(state=State.OK, summary="State: Success"),
        Result(state=State.OK, summary="Job score: 80.00%"),
        Metric("jenkins_job_score", 80.0),
        Result(state=State.OK, summary="Time since last build: 7 days 2 hours"),
        Metric("jenkins_last_build", 612403.0),
        Result(state=State.OK, summary="Time since last successful build: 7 days 2 hours"),
        Metric("jenkins_time_since", 612402.6540000439),
        Result(state=State.OK, summary="Build id: 53"),
        Result(state=State.OK, summary="Build duration: 8 minutes 28 seconds"),
        Metric("jenkins_build_duration", 507.524),
        Result(state=State.OK, summary="Build result: Success"),
    ]


def test_check_job1_item(section: Section) -> None:
    "Never built job, state change to WARN"
    assert list(check_jenkins_jobs("project/Job1", {"job_state": {"notbuilt": 1}}, section)) == [
        Result(state=State.OK, summary="Display name: Job 1"),
        Result(state=State.WARN, summary="State: Not built"),
    ]


def test_check_job2_item(section: Section) -> None:
    """Failed job"""

    assert list(_check_jenkins_jobs("project/Job2", {}, section, now=TEST_TIME)) == [
        Result(state=State.OK, summary="Display name: Job 2"),
        Result(state=State.OK, summary="State: Success"),
        Result(state=State.OK, summary="Job score: 50.00%"),
        Metric("jenkins_job_score", 50.0),
        Result(state=State.OK, summary="Time since last build: 7 days 1 hour"),
        Metric("jenkins_last_build", 610176.0),
        Result(state=State.OK, summary="Time since last successful build: 7 days 1 hour"),
        Metric("jenkins_time_since", 610175.242000103),
        Result(state=State.OK, summary="Build id: 30"),
        Result(state=State.OK, summary="Build duration: 3 minutes 32 seconds"),
        Metric("jenkins_build_duration", 212.036),
        Result(state=State.OK, summary="Build result: Success"),
    ]


def test_check_job3_item(section: Section) -> None:
    assert list(_check_jenkins_jobs("project/Job3", {}, section, now=TEST_TIME)) == [
        Result(state=State.OK, summary="Display name: Job 3"),
        Result(state=State.OK, summary="State: Success"),
        Result(state=State.OK, summary="Job score: 100.00%"),
        Metric("jenkins_job_score", 100.0),
        Result(state=State.OK, summary="Time since last build: 7 days 1 hour"),
        Metric("jenkins_last_build", 609957.0),
        Result(state=State.OK, summary="Time since last successful build: 7 days 1 hour"),
        Metric("jenkins_time_since", 609956.5680000782),
        Result(state=State.OK, summary="Build id: 26"),
        Result(state=State.OK, summary="Build duration: 3 minutes 14 seconds"),
        Metric("jenkins_build_duration", 193.715),
        Result(state=State.CRIT, summary="Build result: Failure"),
    ]


def test_check_job3_item_with_params(section: Section) -> None:
    assert list(
        _check_jenkins_jobs(
            "project/Job3",
            {
                "build_result": {
                    "success": 0,
                    "unstable": 0,
                    "failure": 0,
                    "aborted": 0,
                    "null": 0,
                    "none": 0,
                }
            },
            section,
            now=TEST_TIME,
        )
    ) == [
        Result(state=State.OK, summary="Display name: Job 3"),
        Result(state=State.OK, summary="State: Success"),
        Result(state=State.OK, summary="Job score: 100.00%"),
        Metric("jenkins_job_score", 100.0),
        Result(state=State.OK, summary="Time since last build: 7 days 1 hour"),
        Metric("jenkins_last_build", 609957.0),
        Result(state=State.OK, summary="Time since last successful build: 7 days 1 hour"),
        Metric("jenkins_time_since", 609956.5680000782),
        Result(state=State.OK, summary="Build id: 26"),
        Result(state=State.OK, summary="Build duration: 3 minutes 14 seconds"),
        Metric("jenkins_build_duration", 193.715),
        Result(state=State.OK, summary="Build result: Failure"),
    ]
