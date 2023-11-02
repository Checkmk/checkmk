#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from base64 import b64decode
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from pathlib import Path

import xmltodict
from pydantic import BaseModel, BeforeValidator, Field, Json, RootModel, TypeAdapter
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


class RCCSetupFailures(BaseModel, frozen=True):
    telemetry_disabling: Sequence[str]
    shared_holotree: Sequence[str]
    holotree_init: Sequence[str]


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


class RebotOutcomeResult(Enum):
    Ok: RebotResult


class RebotOutcomeError(Enum):
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


class Outcome(Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Test(BaseModel, frozen=True):
    name: str
    id_: str
    status: Outcome
    starttime: datetime
    endtime: datetime


class Result(BaseModel, frozen=True):
    suite_name: str
    tests: Sequence[Test]
    xml: str
    html: bytes

    def decode_html(self) -> str:
        return b64decode(self.html).decode("utf-8")


class ConfigReadingError(BaseModel, frozen=True):
    config_reading_error: str


class RobotFrameworkConfig(BaseModel, frozen=True):
    robot_target: Path
    command_line_args: Sequence[str] = Field(default=[])


class ExecutionConfig(BaseModel, frozen=True):
    n_retries_max: int
    retry_strategy: str
    execution_interval_seconds: int
    timeout: int


class EnvironmentConfigSystem(Enum):
    System = "System"


class RCCEnvironmentConfig(BaseModel, frozen=True):
    robot_yaml_path: Path
    build_timeout: int
    env_json_path: Path | None


class EnvironmentConfigRcc(BaseModel, frozen=True):
    Rcc: RCCEnvironmentConfig


class SessionConfigCurrent(Enum):
    Current = "Current"


class UserSessionConfig(BaseModel, frozen=True):
    user_name: str


class SessionConfigSpecificUser(BaseModel, frozen=True):
    SpecificUser: UserSessionConfig


class SuiteConfig(BaseModel, frozen=True):
    robot_framework_config: RobotFrameworkConfig
    execution_config: ExecutionConfig
    environment_config: EnvironmentConfigSystem | EnvironmentConfigRcc
    session_config: SessionConfigCurrent | SessionConfigSpecificUser


class Config(BaseModel, frozen=True):
    working_directory: str
    results_directory: str
    rcc_binary_path: str
    suites: Mapping[str, SuiteConfig]


class ConfigFileContent(BaseModel, frozen=True):
    config_file_content: Json[Config]


Section = list[
    Result | ConfigFileContent | SuiteExecutionReport | EnvironmentBuildStatuses | RCCSetupFailures
]

SubSection = (
    Result
    | ConfigReadingError
    | ConfigFileContent
    | SuiteExecutionReport
    | EnvironmentBuildStatuses
    | RCCSetupFailures
)


def _parse_line(line: str) -> SubSection:
    adapter = TypeAdapter(SubSection)
    return adapter.validate_json(line)  # type: ignore[return-value]


def parse(string_table: Sequence[Sequence[str]]) -> Section:
    subsections = [_parse_line(line[0]) for line in string_table]
    results = [
        s
        for s in subsections
        if isinstance(
            s,
            (
                Result,
                ConfigFileContent,
                SuiteExecutionReport,
                EnvironmentBuildStatuses,
                RCCSetupFailures,
            ),
        )
    ]
    return Section(results)
