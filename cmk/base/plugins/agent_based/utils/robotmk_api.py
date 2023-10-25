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


class JSON(BaseModel, frozen=True):
    pass


class EnvironmentBuildStatus(enum.Enum):
    Success = "Success"
    Failure = "Failure"
    Timeout = "Timeout"
    NotNeeded = "NotNeeded"
    Pending = "Pending"
    InProgress = "InProgress"


class AttemptOutcome(enum.Enum):
    AllTestsPassed = "AllTestsPassed"
    TestFailures = "TestFailures"
    RobotFrameworkFailure = "RobotFrameworkFailure"
    EnvironmentFailure = "EnvironmentFailure"
    TimedOut = "TimedOut"
    OtherError = "OtherError"


class EnvironmentBuild(RootModel, frozen=True):
    root: dict[str, EnvironmentBuildStatus]


def _parse_xml(xml_value: str) -> Rebot:
    return Rebot.model_validate(xmltodict.parse(xml_value))


class RebotResult(JSON, frozen=True):
    xml: Annotated[Rebot, BeforeValidator(_parse_xml)]
    html_base64: str


class RebotOutcome(JSON, frozen=True):
    Ok: RebotResult | None = Field(default=None)
    Error: str | None = Field(default=None)


class AttemptsOutcome(JSON, frozen=True):
    attempts: list[AttemptOutcome]
    rebot: RebotOutcome


class ExecutionReport(JSON, frozen=True):
    Executed: AttemptsOutcome
    AlreadyRunning: Literal["AlreadyRunning"] | None = Field(default=None)


class SuiteExecutionReport(JSON, frozen=True):
    suite_name: str
    outcome: ExecutionReport


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Test(JSON, frozen=True):
    name: str
    id_: str
    status: Outcome
    starttime: datetime
    endtime: datetime


class Result(JSON, frozen=True):
    suite_name: str
    tests: list[Test]
    xml: str
    html: bytes

    def decode_html(self) -> str:
        return b64decode(self.html).decode("utf-8")


class ConfigReadingError(JSON, frozen=True):
    config_reading_error: str


class RobotFrameworkConfig(JSON, frozen=True):
    robot_target: str
    variable_file: str
    argument_file: str | None
    retry_strategy: str


class ExecutionConfig(JSON, frozen=True):
    n_retries_max: int
    execution_interval_seconds: int
    timeout: int


class EnvironmentConfig(JSON, frozen=True):
    type: str
    binary_path: str
    robot_yaml_path: str
    build_timeout: int


class SessionConfig(JSON, frozen=True):
    type: str


class SuiteConfig(JSON, frozen=True):
    robot_framework_config: RobotFrameworkConfig
    execution_config: ExecutionConfig
    environment_config: EnvironmentConfig
    session_config: SessionConfig


class ConfigFileValue(JSON, frozen=True):
    working_directory: str
    results_directory: str
    suites: dict[str, SuiteConfig]


class ConfigFileContent(JSON, frozen=True):
    config_file_content: Json[ConfigFileValue]


Section = list[Result | ConfigFileContent | SuiteExecutionReport | EnvironmentBuild]

SubSection = (
    Result | ConfigReadingError | ConfigFileContent | SuiteExecutionReport | EnvironmentBuild
)


def _parse_line(line: str) -> SubSection:
    adapter = TypeAdapter(SubSection)
    return adapter.validate_json(line)  # type: ignore[return-value]


def parse(string_table: Sequence[Sequence[str]]) -> Section:
    subsections = [_parse_line(line[0]) for line in string_table]
    results = [
        s
        for s in subsections
        if isinstance(s, (Result, ConfigFileContent, SuiteExecutionReport, EnvironmentBuild))
    ]
    return Section(results)
