#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import Enum
from itertools import chain
from pathlib import Path
from time import time
from typing import assert_never

from pydantic import BaseModel, Field, RootModel, TypeAdapter

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class ConfigFileContent(BaseModel, frozen=True):
    FileContent: str


class ConfigReadingError(BaseModel, frozen=True):
    ReadingError: str


class RobotFrameworkConfig(BaseModel, frozen=True):
    robot_target: Path
    command_line_args: Sequence[str] = Field(default=[])


class ExecutionConfig(BaseModel, frozen=True):
    n_attempts_max: int
    retry_strategy: str
    execution_interval_seconds: int
    timeout: int


class EnvironmentConfigSystem(Enum):
    System = "System"


class RccConfig(BaseModel, frozen=True):
    robot_yaml_path: Path
    build_timeout: int
    env_json_path: Path | None


class EnvironmentConfigRcc(BaseModel, frozen=True):
    Rcc: RccConfig


class SessionConfigCurrent(Enum):
    Current = "Current"


class UserSessionConfig(BaseModel, frozen=True):
    user_name: str


class SessionConfigSpecificUser(BaseModel, frozen=True):
    SpecificUser: UserSessionConfig


class SourceHost(Enum):
    Source = "Source"


class PiggybackHost(BaseModel, frozen=True):
    Piggyback: str


class SuiteConfig(BaseModel, frozen=True):
    robot_framework_config: RobotFrameworkConfig
    execution_config: ExecutionConfig
    environment_config: EnvironmentConfigSystem | EnvironmentConfigRcc
    session_config: SessionConfigCurrent | SessionConfigSpecificUser
    host: SourceHost | PiggybackHost


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


class EnvironmentBuildStates(RootModel, frozen=True):
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


def parse_robotmk_environment_build_states(
    string_table: StringTable,
) -> EnvironmentBuildStates | None:
    return EnvironmentBuildStates.model_validate_json(string_table[0][0]) if string_table else None


register.agent_section(
    name="robotmk_environment_build_states",
    parse_function=parse_robotmk_environment_build_states,
)


class SchedulerPhase(Enum):
    RCCSetup = "RCCSetup"
    EnvironmentBuilding = "EnvironmentBuilding"
    Scheduling = "Scheduling"


def parse_robotmk_scheduler_phase(
    string_table: StringTable,
) -> SchedulerPhase | None:
    return SchedulerPhase(string_table[0][0].strip('"'))


register.agent_section(
    name="robotmk_scheduler_phase",
    parse_function=parse_robotmk_scheduler_phase,
)


def discover_scheduler_status(
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_scheduler_phase: SchedulerPhase | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
    section_robotmk_environment_build_states: EnvironmentBuildStates | None,
) -> DiscoveryResult:
    if section_robotmk_config:
        yield Service()


def check_scheduler_status(
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_scheduler_phase: SchedulerPhase | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
    section_robotmk_environment_build_states: EnvironmentBuildStates | None,
) -> CheckResult:
    yield from _check_scheduler_status(
        section_robotmk_config=section_robotmk_config,
        section_robotmk_scheduler_phase=section_robotmk_scheduler_phase,
        section_robotmk_rcc_setup_failures=section_robotmk_rcc_setup_failures,
        section_robotmk_environment_build_states=section_robotmk_environment_build_states,
        now=time(),
    )


def _check_scheduler_status(
    *,
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_scheduler_phase: SchedulerPhase | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
    section_robotmk_environment_build_states: EnvironmentBuildStates | None,
    now: float,
) -> CheckResult:
    if not section_robotmk_config:
        return

    yield from _check_config(section_robotmk_config)

    if section_robotmk_scheduler_phase:
        yield Result(
            state=State.OK,
            summary=f"Current phase: {_render_scheduler_phase(section_robotmk_scheduler_phase)}",
        )

    if section_robotmk_rcc_setup_failures:
        yield from _check_rcc_setup_failures(section_robotmk_rcc_setup_failures)

    if section_robotmk_environment_build_states:
        yield from _check_environment_build_states(section_robotmk_environment_build_states, now)


def _check_config(config: Config | ConfigReadingError) -> CheckResult:
    if isinstance(config, ConfigReadingError):
        yield Result(
            state=State.CRIT,
            summary="Error while reading configuration",
            details=f"{config.ReadingError}",
        )
        return
    if not config.suites:
        yield Result(
            state=State.WARN,
            summary="No suites configured",
        )
        return

    yield Result(
        state=State.OK,
        summary=(
            f"{len(config.suites)} suite{'' if len(config.suites) == 1 else 's'} configured "
            f"({', '.join(config.suites)})"
        ),
    )

    for suite_name, suite_config in config.suites.items():
        yield Result(state=State.OK, notice=_render_suite_config(suite_name, suite_config))


def _render_suite_config(suite_name: str, suite_config: SuiteConfig) -> str:
    return "\n".join(
        [
            f"Configuration of suite {suite_name}",
            f"- Scheduling interval: {render.timespan(suite_config.execution_config.execution_interval_seconds)}",
            f"- RCC: {'Yes' if isinstance(suite_config.environment_config, EnvironmentConfigRcc) else 'No'}",
            f"- Maximum number of attempts: {suite_config.execution_config.n_attempts_max}",
        ]
        + (
            [f"- Assigned to host: {suite_config.host.Piggyback}"]
            if isinstance(suite_config.host, PiggybackHost)
            else []
        )
    )


def _render_scheduler_phase(scheduler_phase: SchedulerPhase) -> str:
    match scheduler_phase:
        case SchedulerPhase.RCCSetup:
            return "RCC setup"
        case SchedulerPhase.EnvironmentBuilding:
            return "Environment building"
        case SchedulerPhase.Scheduling:
            return "Suite scheduling"
        case _:
            assert_never(scheduler_phase)


def _check_rcc_setup_failures(rcc_setup_failures: RCCSetupFailures) -> CheckResult:
    yield from (
        Result(
            state=State.CRIT,
            summary=(
                f"{label} failed for the following suites: {', '.join(failures)}. "
                "These suites won't be scheduled."
            ),
        )
        for label, failures in [
            ("Disabling RCC telemetry", rcc_setup_failures.telemetry_disabling),
            ("Enabling RCC shared holotree", rcc_setup_failures.shared_holotree),
            ("RCC holotree initialization", rcc_setup_failures.holotree_init),
        ]
        if failures
    )


def _check_environment_build_states(
    environment_build_states: EnvironmentBuildStates,
    now: float,
) -> CheckResult:
    yield from chain.from_iterable(
        _check_environment_build_status(suite_name, environment_build_status, now)
        for suite_name, environment_build_status in environment_build_states.root.items()
    )


def _check_environment_build_status(
    suite_name: str,
    environment_build_status: EnvironmentBuildStatusNotNeeded
    | EnvironmentBuildStatusPending
    | EnvironmentBuildStatusSuccess
    | EnvironmentBuildStatusInProgress
    | EnvironmentBuildStatusFailure,
    now: float,
) -> CheckResult:
    match environment_build_status:
        case EnvironmentBuildStatusSuccess():
            yield _check_environment_build_success(suite_name, environment_build_status)
        case EnvironmentBuildStatusInProgress():
            yield _check_environment_build_in_progress(suite_name, environment_build_status, now)
        case EnvironmentBuildStatusFailure():
            yield _check_environment_build_failure(suite_name, environment_build_status.Failure)


def _check_environment_build_success(
    suite_name: str,
    environment_build_success: EnvironmentBuildStatusSuccess,
) -> Result:
    return Result(
        state=State.OK,
        notice=f"Suite {suite_name}: Environment build took {render.timespan(environment_build_success.duration)}",
    )


def _check_environment_build_in_progress(
    suite_name: str,
    environment_build_in_progress: EnvironmentBuildStatusInProgress,
    now: float,
) -> Result:
    return Result(
        state=State.OK,
        summary=f"Suite {suite_name}: Environment build currently running for {render.timespan(now - environment_build_in_progress.start_time)}",
    )


def _check_environment_build_failure(
    suite_name: str,
    environment_build_failure: EnvironmentBuildStatusErrorNonZeroExit
    | EnvironmentBuildStatusErrorTimeout
    | EnviromentBuildStatusErrorMessage,
) -> Result:
    match environment_build_failure:
        case EnvironmentBuildStatusErrorNonZeroExit():
            return Result(
                state=State.CRIT,
                summary=f"Suite {suite_name}: Environment building failed. Suite won't be scheduled.",
            )
        case EnvironmentBuildStatusErrorTimeout():
            return Result(
                state=State.CRIT,
                summary=f"Suite {suite_name}: Environment building timed out. Suite won't be scheduled.",
            )
        case EnviromentBuildStatusErrorMessage():
            return Result(
                state=State.CRIT,
                summary=f"Suite {suite_name}: Error while attempting to build environment, see service details. Suite won't be scheduled.",
                details=environment_build_failure.Error,
            )


register.check_plugin(
    name="robotmk_scheduler_status",
    sections=[
        "robotmk_config",
        "robotmk_scheduler_phase",
        "robotmk_rcc_setup_failures",
        "robotmk_environment_build_states",
    ],
    service_name="RMK Scheduler Status",
    discovery_function=discover_scheduler_status,
    check_function=check_scheduler_status,
)
