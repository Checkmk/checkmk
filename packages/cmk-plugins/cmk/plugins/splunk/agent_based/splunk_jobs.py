#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_jobs>>>
# 2019-05-16T11:17:00.000+00:00, splunk-system-user, app, DONE, True
# 2019-05-16T10:13:00.000+00:00, admin, app, FAILED, True

import dataclasses
import datetime
from typing import NotRequired, Self, TypedDict

import pydantic

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

FAILED_DISPATCH_STATE = "FAILED"
"""The dispatch state that determines whether a job failed."""


class Job(pydantic.BaseModel):
    """Information regarding a splunk job."""

    model_config = pydantic.ConfigDict(frozen=True)

    published_at: datetime.datetime
    """When the job was published."""
    author: str
    """Source of the job."""
    application: str
    """Application related to the job."""
    dispatch_state: str
    """The dispatch state of the job."""
    is_zombie: bool
    """Whether a job stopped running, but did not declare that it finished work."""

    def __str__(self) -> str:
        """Represent the job as a string."""
        return f"{render.datetime(self.published_at.timestamp())} - Author: {self.author}, Application: {self.application}, State: {self.dispatch_state}, Zombie: {self.is_zombie}"

    @classmethod
    def from_string_table_item(cls, table: list[str]) -> Self:
        """Build and validate the input from a string table item passed by the agent."""
        payload = dict(zip(cls.__pydantic_fields__, table))
        return cls.model_validate_strings(payload)


@dataclasses.dataclass(frozen=True)
class JobsMetaInfo:
    """Meta information for the parsed jobs."""

    count: int = 0
    """How many jobs."""
    failures: int = 0
    """How many failures were present."""
    zombies: int = 0
    """How many zombies were present."""

    @classmethod
    def from_jobs(cls, jobs: list[Job]) -> Self:
        """Build and validate meta information from jobs."""
        return cls(
            count=len(jobs),
            failures=sum(job.dispatch_state == FAILED_DISPATCH_STATE for job in jobs),
            zombies=sum(job.is_zombie for job in jobs),
        )


@dataclasses.dataclass(frozen=True)
class JobsInfo:
    """Information on all jobs passed to the splunk agent."""

    jobs: tuple[Job, ...]
    """List of parsed jobs."""
    meta: JobsMetaInfo
    """Meta information for the parsed jobs."""


def parse_splunk_jobs(string_table: StringTable) -> JobsInfo:
    """Parse splunk jobs from agent output."""
    jobs = []

    for table in string_table:
        try:
            jobs.append(Job.from_string_table_item(table))
        except pydantic.ValidationError:
            continue  # ignore job if it fails validation

    return JobsInfo(jobs=tuple(jobs), meta=JobsMetaInfo.from_jobs(jobs))


def discover_splunk_jobs(section: JobsInfo) -> DiscoveryResult:
    """Runs empty discovery since there is only a single service."""
    yield Service()


type IntLevels = FixedLevelsT[int]
"""Fixed warn and critical integer threshold."""


class CheckParams(TypedDict):
    """Parameters passed to plugin via ruleset (see defaults)."""

    job_count: NotRequired[IntLevels]
    """The job total threshold."""
    failed_count: NotRequired[IntLevels]
    """The failed jobs threshold."""
    zombie_count: NotRequired[IntLevels]
    """The zombie jobs threshold."""


def render_float_as_int(value: float) -> str:
    """Renders float value as integer string."""
    return f"{value:.0f}"


def check_splunk_jobs(params: CheckParams, section: JobsInfo) -> CheckResult:
    """Checks the splunk jobs section returning valid checkmk results."""
    yield from check_levels(
        section.meta.count,
        levels_upper=params.get("job_count"),
        metric_name="job_total",
        render_func=render_float_as_int,
        label="Job count",
    )
    yield from check_levels(
        section.meta.failures,
        levels_upper=params.get("failed_count"),
        metric_name="failed_total",
        render_func=render_float_as_int,
        label="Failed jobs",
    )
    yield from check_levels(
        section.meta.zombies,
        levels_upper=params.get("zombie_count"),
        metric_name="zombie_total",
        render_func=render_float_as_int,
        label="Zombie jobs",
    )
    # NOTE: this is a bit of a hack to show job information as details.
    yield from (Result(state=State.OK, notice="-", details=str(job)) for job in section.jobs)


agent_section_splunk_jobs = AgentSection(
    name="splunk_jobs",
    parse_function=parse_splunk_jobs,
)

check_plugin_splunk_jobs = CheckPlugin(
    name="splunk_jobs",
    service_name="Splunk Jobs",
    discovery_function=discover_splunk_jobs,
    check_function=check_splunk_jobs,
    check_ruleset_name="splunk_jobs",
    check_default_parameters=CheckParams(),
)
