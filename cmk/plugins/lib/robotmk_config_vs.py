#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict


class RCCProfileConfigCustom(TypedDict):
    http_proxy: Literal["no_proxy"] | tuple[Literal["use_proxy"], str]
    https_proxy: Literal["no_proxy"] | tuple[Literal["use_proxy"], str]


class RFReExecutionConfig(TypedDict):
    strategy: Literal["incremental", "complete"]
    number: int


class ExecutionConfig(TypedDict):
    interval: int
    timeout_per_attempt: int
    rf_re_executions: Literal["no_re_executions"] | tuple[
        Literal["re_executions"], RFReExecutionConfig
    ]


class RobotFrameworkParams(TypedDict, total=False):
    suites: Sequence[str]
    test_names: Sequence[str]
    test_tags_include: Sequence[str]
    test_tags_exclude: Sequence[str]
    variables: Sequence[tuple[str, str]]
    variable_files: Sequence[str]
    argument_files: Sequence[str]


class RccConfig(TypedDict):
    robot_yaml: str
    build_timeout: int
    env_json: NotRequired[str]


class SuiteConfig(TypedDict):
    id: str
    target: str
    execution_config: ExecutionConfig
    robot_framework_params: NotRequired[RobotFrameworkParams]
    rcc: NotRequired[RccConfig | None]
    headed_execution: NotRequired[str]
    piggyback_host: NotRequired[str]
    working_directory_cleanup: (
        tuple[Literal["max_age"], int] | tuple[Literal["max_executions"], int]
    )


class Config(TypedDict):
    suites_base_dir: str
    suites: Sequence[SuiteConfig]
    rcc_profile_config: Literal["default"] | tuple[Literal["custom"], RCCProfileConfigCustom]
