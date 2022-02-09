#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jenkins_jobs>>>
# cmk_140 clang_tidy blue 90 1554371146806 200 SUCCESS 1251806 1554371146806
# cmk_140 cppcheck blue 100 1554371034436 174 SUCCESS 165226 1554371034436
# cmk_140 daily_build blue 100 1562927640962 23672 SUCCESS 1163 1562927640962
# cmk_140 duplicate_code blue 100 1562573916992 1340 SUCCESS 17199 1562573916992
# cmk_140 git_tests blue 100 1562572797049 1732 SUCCESS 50485 1562572797049
# cmk_140 gui_crawl blue 100 1562574249416 1127 SUCCESS 881681 1562574249416

import json
from collections import namedtuple
from time import time
from typing import Any, Dict, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

JenkinsJobInfo: NamedTuple = namedtuple(  # pylint: disable=collections-namedtuple-call
    "JenkinsJobInfo",
    [
        "display_name",
        "name",
        "state",
        "score",
        "last_suc_build",
        "build_id",
        "build_result",
        "build_duration",
        "build_timestamp",
    ],
)

MAP_JOB_STATES = {
    "aborted": {"state": 0, "info": "Aborted"},
    "blue": {"state": 0, "info": "Success"},
    "disabled": {"state": 0, "info": "Disabled"},
    "notbuilt": {"state": 0, "info": "Not built"},
    "red": {"state": 2, "info": "Failed"},
    "yellow": {"state": 1, "info": "Unstable"},
}

MAP_BUILD_STATES = {
    "success": 0,  # no errors
    "unstable": 1,  # some errors but not fatal
    "failure": 2,  # fatal error
    "aborted": 0,  # manually aborted
    "null": 1,  # module was not built
    "none": 0,  # running
}

Section = Mapping[str, JenkinsJobInfo]


def parse_jenkins_jobs(string_table) -> Section:
    parsed: Dict[str, JenkinsJobInfo] = {}

    for line in string_table:
        jenkins_data = json.loads(line[0])

        parsed.update(_handle_job_type(jenkins_data, {}, ""))

    return parsed


register.agent_section(
    name="jenkins_jobs",
    parse_function=parse_jenkins_jobs,
)


def discovery_jenkins_jobs(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_jenkins_jobs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    item_data = section.get(item)
    if item_data is None:
        return

    for job in item_data:
        if job.display_name is not None:
            yield Result(state=State.OK, summary=f"Display name: {job.display_name}")

        job_state = job.state
        if job_state is not None:
            if "grey" in job_state:
                job_state = "aborted"

            job_cleanup = job_state.replace("_anime", "")
            infotext = "State: %s" % MAP_JOB_STATES[job_cleanup]["info"]
            state = MAP_JOB_STATES[job_cleanup]["state"]
            if "_anime" in job_state:
                infotext += " (in progress)"

            yield Result(
                state=State(params.get("job_state", {}).get(job_cleanup, state)), summary=infotext
            )

        if job.score is not None:
            score_key = "jenkins_job_score"
            yield from check_levels(
                job.score,
                metric_name=score_key,
                levels_lower=params.get(score_key),
                render_func=render.percent,
                label="Job score",
            )

        now = time()
        time_since_last_build = None
        if job.build_timestamp is not None:
            time_since_last_build = now - job.build_timestamp
            build_timestamp_key = "jenkins_last_build"
            yield from check_levels(
                time_since_last_build,
                metric_name=build_timestamp_key,
                levels_upper=params.get(build_timestamp_key),
                render_func=render.timespan,
                label="Time since last build",
            )

        time_since_last_suc = None
        if job.last_suc_build is not None:
            time_since_last_suc = now - job.last_suc_build
            time_since_last_suc_key = "jenkins_time_since"
            yield from check_levels(
                time_since_last_suc,
                metric_name=time_since_last_suc_key,
                levels_upper=params.get(time_since_last_suc_key),
                render_func=render.timespan,
                label="Time since last successful build",
            )

        if job.build_id is not None:
            yield from check_levels(
                job.build_id,
                render_func=lambda x: str(int(x)),
                label="Build id",
            )

        if job.build_duration is not None:
            build_duration_key = "jenkins_build_duration"
            yield from check_levels(
                job.build_duration,
                metric_name=build_duration_key,
                levels_upper=params.get(build_duration_key),
                render_func=render.timespan,
                label="Build duration",
            )

        if job.build_result is not None:
            yield Result(
                state=State(
                    params.get("build_result", {}).get(
                        job.build_result, MAP_BUILD_STATES[job.build_result.lower()]
                    )
                ),
                summary="Build result: %s" % job.build_result.title(),
            )


def _handle_single_job(job):
    # key healthReport can have an empty list value
    try:
        health_rp = job["healthReport"][0]["score"]
    except (IndexError, KeyError, TypeError):
        health_rp = None

    # key lastSuccessfulBuild can have None value: {'lastSuccessfulBuild':None}
    try:
        last_sb: Optional[float] = float(job["lastSuccessfulBuild"]["timestamp"]) / 1000.0
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        last_sb = None

    # key lastBuild can have None value: {'lastBuild':None}
    try:
        last_br: Optional[str] = job["lastBuild"]["result"]
        last_bn: Optional[str] = job["lastBuild"]["number"]
        last_bd: Optional[float] = float(job["lastBuild"]["duration"]) / 1000.0
        last_bt: Optional[int] = int(int(job["lastBuild"]["timestamp"]) / 1000)
    except (KeyError, TypeError, ValueError):
        last_br = None
        last_bn = None
        last_bd = None
        last_bt = None

    return JenkinsJobInfo(
        job["displayNameOrNull"],
        job["name"],
        job["color"],
        health_rp,
        last_sb,
        last_bn,
        last_br,
        last_bd,
        last_bt,
    )


def _handle_job_type(data, new_dict, folder=""):
    for job_type in data:
        item_name = folder
        if job_type.get("_class") and job_type["_class"] in [
            "com.cloudbees.hudson.plugins.folder.Folder",
            "org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject",
            "jenkins.branch.OrganizationFolder",
        ]:
            item_name += "%s/" % job_type["name"]
            if job_type.get("jobs") is not None:
                _handle_job_type(job_type["jobs"], new_dict, item_name)
            continue

        if item_name is None:
            item_name = "%s" % job_type["name"]
        else:
            item_name = "%s%s" % (item_name, job_type["name"])

        job = _handle_single_job(job_type)

        new_dict.setdefault("%s" % item_name, []).append(job)

    return new_dict


register.check_plugin(
    name="jenkins_jobs",
    service_name="Jenkins Job %s",
    discovery_function=discovery_jenkins_jobs,
    check_function=check_jenkins_jobs,
    check_default_parameters={},
    check_ruleset_name="jenkins_jobs",
)
