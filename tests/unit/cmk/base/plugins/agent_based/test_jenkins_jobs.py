#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from freezegun import freeze_time

import cmk.base.plugins.agent_based.jenkins_jobs as jn
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric

NOW_SIMULATED = "2021-11-23 13:00:00"


@pytest.fixture(scope="module", name="section")
def _section() -> jn.Section:
    return jn.parse_jenkins_jobs(
        [
            [
                '[{"_class":"jenkins.branch.OrganizationFolder","displayNameOrNull":null,"name":"gitea","healthReport":[],"jobs":[]},{"_class":"com.cloudbees.hudson.plugins.folder.Folder","displayNameOrNull":"Folder1","name":"project","healthReport":[{"score":50}],"jobs":[{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","displayNameOrNull":"Job","name":"Job","color":"blue","healthReport":[{"score":80}],"lastBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","duration":507524,"number":53,"result":"SUCCESS","timestamp":1637059997346},"lastSuccessfulBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","timestamp":1637059997346}},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","displayNameOrNull":"Job 1","name":"Job1","color":"notbuilt","healthReport":[],"lastBuild":"null"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","displayNameOrNull":"Job 2","name":"Job2","color":"blue","healthReport":[{"score":50}],"lastBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","duration":212036,"number":30,"result":"SUCCESS","timestamp":1637062224758},"lastSuccessfulBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","timestamp":1637062224758}},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","displayNameOrNull":"Job 3","name":"Job3","color":"blue","healthReport":[{"score":100}],"lastBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","duration":193715,"number":26,"result":"FAILURE","timestamp":1637062443432},"lastSuccessfulBuild":{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowRun","timestamp":1637062443432}}]}]'
            ]
        ]
    )


def test_discovery(section: jn.Section) -> None:
    assert list(jn.discovery_jenkins_jobs(section)) == [
        jn.Service(item="project/Job"),
        jn.Service(item="project/Job1"),
        jn.Service(item="project/Job2"),
        jn.Service(item="project/Job3"),
    ]


@freeze_time(NOW_SIMULATED)
def test_check_job_item(section: jn.Section) -> None:
    """Successfull job"""
    assert list(jn.check_jenkins_jobs("project/Job", {}, section)) == [
        jn.Result(state=jn.State.OK, summary="Display name: Job"),
        jn.Result(state=jn.State.OK, summary="State: Success"),
        jn.Result(state=jn.State.OK, summary="Job score: 80.00%"),
        Metric("jenkins_job_score", 80.0),
        jn.Result(state=jn.State.OK, summary="Time since last build: 7 days 2 hours"),
        Metric("jenkins_last_build", 612403.0),
        jn.Result(state=jn.State.OK, summary="Time since last successful build: 7 days 2 hours"),
        Metric("jenkins_time_since", 612402.6540000439),
        jn.Result(state=jn.State.OK, summary="Build id: 53"),
        jn.Result(state=jn.State.OK, summary="Build duration: 8 minutes 28 seconds"),
        Metric("jenkins_build_duration", 507.524),
        jn.Result(state=jn.State.OK, summary="Build result: Success"),
    ]


def test_check_job1_item(section: jn.Section) -> None:
    "Never built job, state change to WARN"
    assert list(jn.check_jenkins_jobs("project/Job1", {"job_state": {"notbuilt": 1}}, section)) == [
        jn.Result(state=jn.State.OK, summary="Display name: Job 1"),
        jn.Result(state=jn.State.WARN, summary="State: Not built"),
    ]


@freeze_time(NOW_SIMULATED)
def test_check_job2_item(section: jn.Section) -> None:
    """Failed job"""
    assert list(jn.check_jenkins_jobs("project/Job2", {}, section)) == [
        jn.Result(state=jn.State.OK, summary="Display name: Job 2"),
        jn.Result(state=jn.State.OK, summary="State: Success"),
        jn.Result(state=jn.State.OK, summary="Job score: 50.00%"),
        Metric("jenkins_job_score", 50.0),
        jn.Result(state=jn.State.OK, summary="Time since last build: 7 days 1 hour"),
        Metric("jenkins_last_build", 610176.0),
        jn.Result(state=jn.State.OK, summary="Time since last successful build: 7 days 1 hour"),
        Metric("jenkins_time_since", 610175.242000103),
        jn.Result(state=jn.State.OK, summary="Build id: 30"),
        jn.Result(state=jn.State.OK, summary="Build duration: 3 minutes 32 seconds"),
        Metric("jenkins_build_duration", 212.036),
        jn.Result(state=jn.State.OK, summary="Build result: Success"),
    ]


@freeze_time("2021-11-23 13:00:00")
def test_check_job3_item(section: jn.Section) -> None:
    assert list(jn.check_jenkins_jobs("project/Job3", {}, section)) == [
        jn.Result(state=jn.State.OK, summary="Display name: Job 3"),
        jn.Result(state=jn.State.OK, summary="State: Success"),
        jn.Result(state=jn.State.OK, summary="Job score: 100.00%"),
        Metric("jenkins_job_score", 100.0),
        jn.Result(state=jn.State.OK, summary="Time since last build: 7 days 1 hour"),
        Metric("jenkins_last_build", 609957.0),
        jn.Result(state=jn.State.OK, summary="Time since last successful build: 7 days 1 hour"),
        Metric("jenkins_time_since", 609956.5680000782),
        jn.Result(state=jn.State.OK, summary="Build id: 26"),
        jn.Result(state=jn.State.OK, summary="Build duration: 3 minutes 14 seconds"),
        Metric("jenkins_build_duration", 193.715),
        jn.Result(state=jn.State.CRIT, summary="Build result: Failure"),
    ]
