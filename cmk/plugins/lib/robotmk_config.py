#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import PurePath

from pydantic import BaseModel, Field


class RCCProfileConfig(BaseModel, frozen=True):
    name: str
    path: PurePath


class RCCConfig(BaseModel, frozen=True):
    binary_path: PurePath
    profile_config: RCCProfileConfig | None


class RobotFrameworkConfig(BaseModel, frozen=True):
    robot_target: PurePath
    command_line_args: Sequence[str] = Field(default=[])


class RetryStrategy(Enum):
    INCREMENTAL = "Incremental"
    COMPLETE = "Complete"


class ExecutionConfig(BaseModel, frozen=True):
    n_attempts_max: int
    retry_strategy: RetryStrategy
    execution_interval_seconds: int
    timeout: int


class EnvironmentConfigSystem(Enum):
    System = "System"


class RCCEnvironmentConfig(BaseModel, frozen=True):
    robot_yaml_path: PurePath
    build_timeout: int
    env_json_path: PurePath | None


class EnvironmentConfigRcc(BaseModel, frozen=True):
    Rcc: RCCEnvironmentConfig


class SessionConfigCurrent(Enum):
    Current = "Current"


class UserSessionConfig(BaseModel, frozen=True):
    user_name: str


class SessionConfigSpecificUser(BaseModel, frozen=True):
    SpecificUser: UserSessionConfig


class WorkingDirectoryCleanupConfigMaxAge(BaseModel, frozen=True):
    MaxAgeSecs: int


class WorkingDirectoryCleanupConfigMaxExecutions(BaseModel, frozen=True):
    MaxExecutions: int


class SourceHost(Enum):
    Source = "Source"


class PiggybackHost(BaseModel, frozen=True):
    Piggyback: str


class SuiteConfig(BaseModel, frozen=True):
    robot_framework_config: RobotFrameworkConfig
    execution_config: ExecutionConfig
    environment_config: EnvironmentConfigSystem | EnvironmentConfigRcc
    session_config: SessionConfigCurrent | SessionConfigSpecificUser
    working_directory_cleanup_config: (
        WorkingDirectoryCleanupConfigMaxAge | WorkingDirectoryCleanupConfigMaxExecutions
    )
    host: SourceHost | PiggybackHost


class Config(BaseModel, frozen=True):
    working_directory: PurePath
    results_directory: PurePath
    rcc_config: RCCConfig
    suites: Mapping[str, SuiteConfig]
