#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

import xmltodict
from pydantic import BaseModel, BeforeValidator, Field, RootModel, TypeAdapter
from typing_extensions import Annotated

from .robotmk_parse_xml import Rebot


class EnvironmentBuildStatusSuccess(BaseModel, frozen=True):
    duration: int = Field(alias="Success")


class EnvironmentBuildStatusInProgress(BaseModel, frozen=True):
    start_time: int = Field(alias="InProgress")


class EnvironmentBuildStatusErrorNonZeroExit(Enum):
    NonZeroExit = "NonZeroExit"


class EnvironmentBuildStatusErrorTimeout(Enum):
    Timeout = "Timeout"


class EnviromentBuildStatusErrorMessage(BaseModel):
    Error: str


class EnvironmentBuildStatusFailure(BaseModel):
    Failure: (
        EnvironmentBuildStatusErrorNonZeroExit
        | EnvironmentBuildStatusErrorTimeout
        | EnviromentBuildStatusErrorMessage
    )


class EnvironmentBuildStatusNotNeeded(Enum):
    NotNeeded = "NotNeeded"


class EnvironmentBuildStatusPending(Enum):
    Pending = "Pending"


class EnvironmentBuildStatuses(RootModel, frozen=True):
    root: Mapping[
        str,
        (
            EnvironmentBuildStatusNotNeeded
            | EnvironmentBuildStatusPending
            | EnvironmentBuildStatusSuccess
            | EnvironmentBuildStatusInProgress
            | EnvironmentBuildStatusFailure
        ),
    ]


class AttemptOutcome(Enum):
    AllTestsPassed = "AllTestsPassed"
    TestFailures = "TestFailures"
    RobotFrameworkFailure = "RobotFrameworkFailure"
    EnvironmentFailure = "EnvironmentFailure"
    TimedOut = "TimedOut"


class AttemptOutcomeOtherError(BaseModel, frozen=True):
    OtherError: str


def _parse_xml(xml_value: str) -> Rebot:
    return Rebot.model_validate(xmltodict.parse(xml_value))


class RebotResult(BaseModel, frozen=True):
    xml: Annotated[Rebot, BeforeValidator(_parse_xml)]
    html_base64: str


class RebotOutcomeResult(BaseModel, frozen=True):
    Ok: RebotResult


class RebotOutcomeError(BaseModel, frozen=True):
    Error: str


class AttemptsOutcome(BaseModel, frozen=True):
    attempts: Sequence[AttemptOutcome | AttemptOutcomeOtherError]
    rebot: RebotOutcomeResult | RebotOutcomeError | None


class ExecutionReport(BaseModel, frozen=True):
    Executed: AttemptsOutcome


class ExecutionReportAlreadyRunning(Enum):
    AlreadyRunning = "AlreadyRunning"


class SuiteExecutionReport(BaseModel, frozen=True):
    suite_name: str
    outcome: ExecutionReport | ExecutionReportAlreadyRunning


@dataclass(frozen=True, kw_only=True)
class Section:
    environment_build_statuses: EnvironmentBuildStatuses | None = None
    suite_execution_reports: Sequence[SuiteExecutionReport] = field(default_factory=list)


def parse(string_table: Sequence[Sequence[str]]) -> Section:
    environment_build_statuses: EnvironmentBuildStatuses | None = None
    suite_execution_reports = []

    type_adapter = TypeAdapter(SuiteExecutionReport | EnvironmentBuildStatuses)
    for sub_section in (type_adapter.validate_json(line[0]) for line in string_table):
        match sub_section:
            case EnvironmentBuildStatuses():
                environment_build_statuses = sub_section
            case SuiteExecutionReport():
                suite_execution_reports.append(sub_section)

    return Section(
        environment_build_statuses=environment_build_statuses,
        suite_execution_reports=suite_execution_reports,
    )
