#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import Enum
from itertools import chain
from time import time
from typing import assert_never, Iterator, Literal

from pydantic import BaseModel, Field, RootModel, TypeAdapter

from cmk.plugins.lib.robotmk_config import Config, EnvironmentConfigRcc, PiggybackHost, SuiteConfig

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class ConfigFileContent(BaseModel, frozen=True):
    FileContent: str


class ConfigReadingError(BaseModel, frozen=True):
    ReadingError: str


ConfigAdapter = TypeAdapter(ConfigFileContent | ConfigReadingError)


def parse_robotmk_config(string_table: StringTable) -> Config | ConfigReadingError | None:
    if not string_table:
        return None

    match (config_data := ConfigAdapter.validate_json(string_table[0][0])):
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
    long_path_support: Sequence[str]
    shared_holotree: Sequence[str]
    holotree_init: Sequence[str]


def parse_robotmk_rcc_setup_failures(string_table: StringTable) -> RCCSetupFailures | None:
    return RCCSetupFailures.model_validate_json(string_table[0][0]) if string_table else None


register.agent_section(
    name="robotmk_rcc_setup_failures",
    parse_function=parse_robotmk_rcc_setup_failures,
)


class BuildOutcomeSuccess(BaseModel, frozen=True):
    duration: int = Field(alias="Success")


class BuildOutcomeError(BaseModel, frozen=True):
    Error: str


BuildOutcome = (
    Literal["NotNeeded", "Timeout", "Terminated", "NonZeroExit"]
    | BuildOutcomeError
    | BuildOutcomeSuccess
)


class BuildStageComplete(BaseModel, frozen=True):
    Complete: BuildOutcome


class BuildStageInProgress(BaseModel, frozen=True):
    start_time: int = Field(alias="InProgress")


EnvironmentBuildStage = Literal["Pending"] | BuildStageComplete | BuildStageInProgress


class EnvironmentBuildStages(RootModel, frozen=True):
    root: Mapping[str, EnvironmentBuildStage]


def parse_robotmk_environment_build_states(
    string_table: StringTable,
) -> EnvironmentBuildStages | None:
    return EnvironmentBuildStages.model_validate_json(string_table[0][0]) if string_table else None


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
    section_robotmk_environment_build_states: EnvironmentBuildStages | None,
) -> DiscoveryResult:
    if section_robotmk_config:
        yield Service()


def check_scheduler_status(
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_scheduler_phase: SchedulerPhase | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
    section_robotmk_environment_build_states: EnvironmentBuildStages | None,
) -> CheckResult:
    yield from _check_scheduler_status(
        section_robotmk_config=section_robotmk_config,
        section_robotmk_scheduler_phase=section_robotmk_scheduler_phase,
        section_robotmk_rcc_setup_failures=section_robotmk_rcc_setup_failures,
        section_robotmk_environment_build_stages=section_robotmk_environment_build_states,
        now=time(),
    )


def _check_scheduler_status(
    *,
    section_robotmk_config: Config | ConfigReadingError | None,
    section_robotmk_scheduler_phase: SchedulerPhase | None,
    section_robotmk_rcc_setup_failures: RCCSetupFailures | None,
    section_robotmk_environment_build_stages: EnvironmentBuildStages | None,
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

    if section_robotmk_environment_build_stages:
        yield from _check_environment_build_states(section_robotmk_environment_build_stages, now)


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

    for suite_id, suite_config in config.suites.items():
        yield Result(state=State.OK, notice=_render_suite_config(suite_id, suite_config))


def _render_suite_config(suite_id: str, suite_config: SuiteConfig) -> str:
    return "\n".join(
        [
            f"Configuration of suite {suite_id}",
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
            ("Enabling RCC long path support", rcc_setup_failures.long_path_support),
            ("Enabling RCC shared holotree", rcc_setup_failures.shared_holotree),
            ("RCC holotree initialization", rcc_setup_failures.holotree_init),
        ]
        if failures
    )


def _check_environment_build_states(
    environment_build_stages: EnvironmentBuildStages,
    now: float,
) -> CheckResult:
    yield from chain.from_iterable(
        _check_environment_build_status(suite_id, environment_build_status, now)
        for suite_id, environment_build_status in environment_build_stages.root.items()
    )


def _check_environment_build_status(
    suite_id: str,
    environment_build_stage: EnvironmentBuildStage,
    now: float,
) -> CheckResult:
    match environment_build_stage:
        case BuildStageInProgress():
            yield _check_environment_build_in_progress(suite_id, environment_build_stage, now)
        case BuildStageComplete():
            yield from _check_environment_build_complete(suite_id, environment_build_stage.Complete)


def _check_environment_build_in_progress(
    suite_id: str,
    environment_build_stage: BuildStageInProgress,
    now: float,
) -> Result:
    return Result(
        state=State.OK,
        summary=f"Suite {suite_id}: Environment build currently running for {render.timespan(now - environment_build_stage.start_time)}",
    )


def _check_environment_build_complete(
    suite_id: str, build_outcome: BuildOutcome
) -> Iterator[Result]:
    match build_outcome:
        case "NonZeroExit":
            yield Result(
                state=State.CRIT,
                summary=f"Suite {suite_id}: Environment building failed. Suite won't be scheduled.",
            )
        case "Timeout":
            yield Result(
                state=State.CRIT,
                summary=f"Suite {suite_id}: Environment building timed out. Suite won't be scheduled.",
            )
        case "Terminated":
            yield Result(
                state=State.CRIT,
                summary=f"Suite {suite_id}: Scheduler was terminated.",
            )
        case BuildOutcomeError():
            yield Result(
                state=State.CRIT,
                summary=f"Suite {suite_id}: Error while attempting to build environment, see service details. Suite won't be scheduled.",
                details=build_outcome.Error,
            )
        case BuildOutcomeSuccess():
            yield Result(
                state=State.OK,
                notice=f"Suite {suite_id}: Environment build took {render.timespan(build_outcome.duration)}",
            )
        case "NotNeeded":
            pass


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
