#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class ConfigFileContent(BaseModel, frozen=True):
    FileContent: str


class ConfigReadingError(BaseModel, frozen=True):
    ReadingError: str


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


class EnvironmentConfigRcc(BaseModel, frozen=True):
    type: Literal["Rcc"]
    robot_yaml_path: Path
    build_timeout: int
    env_json_path: Path | None


class SessionConfigCurrentEnum(Enum):
    Current = "Current"


class SessionConfigCurrent(BaseModel, frozen=True):
    type: SessionConfigCurrentEnum


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


def parse_robotmk_config(string_table: StringTable) -> Config | ConfigReadingError | None:
    if not string_table:
        return None

    match (
        config_data := TypeAdapter(ConfigFileContent | ConfigReadingError).validate_json(
            string_table[0][0]
        )
    ):
        case ConfigReadingError():
            return config_data
        case ConfigFileContent():
            return Config.model_validate_json(config_data.FileContent)

    raise ValueError("Invalid configuration data")


register.agent_section(
    name="robotmk_config",
    parse_function=parse_robotmk_config,
)


class RCCSetupFailures(BaseModel, frozen=True):
    telemetry_disabling: Sequence[str]
    shared_holotree: Sequence[str]
    holotree_init: Sequence[str]


def parse_robotmk_rcc_setup_failures(string_table: StringTable) -> RCCSetupFailures | None:
    return RCCSetupFailures.model_validate_json(string_table[0][0]) if string_table else None


register.agent_section(
    name="robotmk_rcc_setup_failures",
    parse_function=parse_robotmk_rcc_setup_failures,
)


def discover_scheduler_status(
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
) -> DiscoveryResult:
    if section_robotmk_config:
        yield Service()


def check_scheduler_status(
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
) -> CheckResult:
    if not section_robotmk_config:
        return
    # TODO: Determine the conditions for the status
    yield Result(state=State.OK, summary="The Scheduler status is OK")


register.check_plugin(
    name="robotmk_scheduler_status",
    sections=["robotmk_config", "robotmk_rcc_setup_failures"],
    service_name="Robotmk Scheduler Status",
    discovery_function=discover_scheduler_status,
    check_function=check_scheduler_status,
)
