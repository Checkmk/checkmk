#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Should be replaced by external package

import enum
from base64 import b64decode
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

import xmltodict
from pydantic import BaseModel, BeforeValidator, Field, Json, RootModel, TypeAdapter
from typing_extensions import Annotated

from .robotmk_parse_xml import Rebot


class EnvironmentBuildStatusSuccess(BaseModel, frozen=True):
    duration: int = Field(alias="Success")


class EnvironmentBuildStatusInProgress(BaseModel, frozen=True):
    start_time: int = Field(alias="InProgress")


class EnvironmentBuildStatusError(enum.Enum):
    NonZeroExit = "NonZeroExit"
    Timeout = "Timeout"


class EnviromentBuildStatusErrorWithDescription(BaseModel):
    Error: str


class EnvironmentBuildStatusFailure(BaseModel):
    Failure: EnvironmentBuildStatusError | EnviromentBuildStatusErrorWithDescription


class EnvironmentBuildStatusEnum(enum.Enum):
    NotNeeded = "NotNeeded"
    Pending = "Pending"


EnvironmentBuildStatuses = (
    EnvironmentBuildStatusEnum
    | EnvironmentBuildStatusSuccess
    | EnvironmentBuildStatusInProgress
    | EnvironmentBuildStatusFailure
)


class EnvironmentBuild(RootModel, frozen=True):
    root: dict[str, EnvironmentBuildStatuses]


class RCCSetupFailures(BaseModel, frozen=True):
    telemetry_disabling: list[str]
    shared_holotree: list[str]
    holotree_init: list[str]


class AttemptOutcome(enum.Enum):
    AllTestsPassed = "AllTestsPassed"
    TestFailures = "TestFailures"
    RobotFrameworkFailure = "RobotFrameworkFailure"
    EnvironmentFailure = "EnvironmentFailure"
    TimedOut = "TimedOut"
    OtherError = "OtherError"


def _parse_xml(xml_value: str) -> Rebot:
    return Rebot.model_validate(xmltodict.parse(xml_value))


class RebotResult(BaseModel, frozen=True):
    xml: Annotated[Rebot, BeforeValidator(_parse_xml)]
    html_base64: str


class RebotOutcome(BaseModel, frozen=True):
    Ok: RebotResult | None = Field(default=None)
    Error: str | None = Field(default=None)


class AttemptsOutcome(BaseModel, frozen=True):
    attempts: list[AttemptOutcome]
    rebot: RebotOutcome


class ExecutionReport(BaseModel, frozen=True):
    Executed: AttemptsOutcome
    AlreadyRunning: Literal["AlreadyRunning"] | None = Field(default=None)


class SuiteExecutionReport(BaseModel, frozen=True):
    suite_name: str
    outcome: ExecutionReport


class Outcome(enum.Enum):
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
    tests: list[Test]
    xml: str
    html: bytes

    def decode_html(self) -> str:
        return b64decode(self.html).decode("utf-8")


class ConfigReadingError(BaseModel, frozen=True):
    config_reading_error: str


class RobotFrameworkConfig(BaseModel, frozen=True):
    robot_target: str
    command_line_args: list[str] = Field(default=[])


class ExecutionConfig(BaseModel, frozen=True):
    n_retries_max: int
    retry_strategy: str
    execution_interval_seconds: int
    timeout: int


class EnvironmentConfig(BaseModel, frozen=True):
    type: str
    robot_yaml_path: str
    build_timeout: int
    env_json_path: str | None = None


class SessionConfig(BaseModel, frozen=True):
    type: str


class SuiteConfig(BaseModel, frozen=True):
    robot_framework_config: RobotFrameworkConfig
    execution_config: ExecutionConfig
    environment_config: EnvironmentConfig
    session_config: SessionConfig


class ConfigFileValue(BaseModel, frozen=True):
    working_directory: str
    results_directory: str
    rcc_binary_path: str
    suites: dict[str, SuiteConfig]


class ConfigFileContent(BaseModel, frozen=True):
    config_file_content: Json[ConfigFileValue]


Section = list[
    Result | ConfigFileContent | SuiteExecutionReport | EnvironmentBuild | RCCSetupFailures
]

SubSection = (
    Result
    | ConfigReadingError
    | ConfigFileContent
    | SuiteExecutionReport
    | EnvironmentBuild
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
            s, (Result, ConfigFileContent, SuiteExecutionReport, EnvironmentBuild, RCCSetupFailures)
        )
    ]
    return Section(results)
