#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.robotmk_scheduler_status import (
    _check_scheduler_status,
    ConfigReadingError,
    discover_scheduler_status,
    EnviromentBuildStatusErrorMessage,
    EnvironmentBuildStates,
    EnvironmentBuildStatusErrorNonZeroExit,
    EnvironmentBuildStatusFailure,
    EnvironmentBuildStatusInProgress,
    EnvironmentBuildStatusNotNeeded,
    EnvironmentBuildStatusSuccess,
    RCCSetupFailures,
    SchedulerPhase,
)

from cmk.plugins.lib.robotmk_config import (
    Config,
    EnvironmentConfigRcc,
    EnvironmentConfigSystem,
    ExecutionConfig,
    PiggybackHost,
    RccConfig,
    RetryStrategy,
    RobotFrameworkConfig,
    SessionConfigCurrent,
    SessionConfigSpecificUser,
    SourceHost,
    SuiteConfig,
    UserSessionConfig,
    WorkingDirectoryCleanupConfigMaxAge,
    WorkingDirectoryCleanupConfigMaxExecutions,
)

_CONFIG = Config(
    working_directory=Path("C:\\robotmk\\working"),
    results_directory=Path("C:\\robotmk\\results"),
    rcc_binary_path=Path("C:\\robotmk\\rcc.exe"),
    suites={
        "system": SuiteConfig(
            robot_framework_config=RobotFrameworkConfig(
                robot_target=Path("C:\\robotmk\\suites\\system\\tasks.robot"),
            ),
            execution_config=ExecutionConfig(
                n_attempts_max=1,
                retry_strategy=RetryStrategy.COMPLETE,
                execution_interval_seconds=600,
                timeout=30,
            ),
            environment_config=EnvironmentConfigSystem.System,
            session_config=SessionConfigCurrent.Current,
            working_directory_cleanup_config=WorkingDirectoryCleanupConfigMaxAge(MaxAgeSecs=3600),
            host=SourceHost.Source,
        ),
        "rcc": SuiteConfig(
            robot_framework_config=RobotFrameworkConfig(
                robot_target=Path("C:\\robotmk\\suites\\rcc\\tasks.robot"),
            ),
            execution_config=ExecutionConfig(
                n_attempts_max=2,
                retry_strategy=RetryStrategy.INCREMENTAL,
                execution_interval_seconds=600,
                timeout=100,
            ),
            environment_config=EnvironmentConfigRcc(
                Rcc=RccConfig(
                    robot_yaml_path=Path("C:\\robotmk\\suites\\rcc\\robot.yaml"),
                    build_timeout=300,
                    env_json_path=None,
                )
            ),
            session_config=SessionConfigSpecificUser(
                SpecificUser=UserSessionConfig(user_name="synth_mon")
            ),
            working_directory_cleanup_config=WorkingDirectoryCleanupConfigMaxAge(MaxAgeSecs=3600),
            host=SourceHost.Source,
        ),
        "piggyback": SuiteConfig(
            robot_framework_config=RobotFrameworkConfig(
                robot_target=Path("C:\\robotmk\\suites\\piggyback\\tasks.robot"),
            ),
            execution_config=ExecutionConfig(
                n_attempts_max=1,
                retry_strategy=RetryStrategy.COMPLETE,
                execution_interval_seconds=200,
                timeout=100,
            ),
            environment_config=EnvironmentConfigRcc(
                Rcc=RccConfig(
                    robot_yaml_path=Path("C:\\robotmk\\suites\\piggyback\\robot.yaml"),
                    build_timeout=300,
                    env_json_path=None,
                )
            ),
            session_config=SessionConfigCurrent.Current,
            working_directory_cleanup_config=WorkingDirectoryCleanupConfigMaxExecutions(
                MaxExecutions=10
            ),
            host=PiggybackHost(Piggyback="synth_mon_host"),
        ),
    },
)


def test_discover_scheduler_status_standard() -> None:
    assert list(
        discover_scheduler_status(
            section_robotmk_config=_CONFIG,
            section_robotmk_scheduler_phase=None,
            section_robotmk_rcc_setup_failures=None,
            section_robotmk_environment_build_states=None,
        )
    ) == [Service()]


def test_discover_scheduler_status_no_data() -> None:
    assert not list(
        discover_scheduler_status(
            section_robotmk_config=None,
            section_robotmk_scheduler_phase=None,
            section_robotmk_rcc_setup_failures=None,
            section_robotmk_environment_build_states=None,
        )
    )


def test_check_scheduler_status_standard() -> None:
    assert list(
        _check_scheduler_status(
            section_robotmk_config=_CONFIG,
            section_robotmk_scheduler_phase=SchedulerPhase.Scheduling,
            section_robotmk_rcc_setup_failures=RCCSetupFailures(
                telemetry_disabling=[],
                long_path_support=[],
                shared_holotree=[],
                holotree_init=[],
            ),
            section_robotmk_environment_build_states=EnvironmentBuildStates(
                root={
                    "system": EnvironmentBuildStatusNotNeeded.NotNeeded,
                    "rcc": EnvironmentBuildStatusSuccess(Success=67),
                    "piggyback": EnvironmentBuildStatusSuccess(Success=123),
                }
            ),
            now=1,
        )
    ) == [
        Result(state=State.OK, summary="3 suites configured (system, rcc, piggyback)"),
        Result(
            state=State.OK,
            notice="Configuration of suite system\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: No\n- Maximum number of attempts: 1",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite rcc\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: Yes\n- Maximum number of attempts: 2",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite piggyback\n- Scheduling interval: 3 minutes 20 seconds\n- RCC: Yes\n- Maximum number of attempts: 1\n- Assigned to host: synth_mon_host",
        ),
        Result(state=State.OK, summary="Current phase: Suite scheduling"),
        Result(state=State.OK, notice="Suite rcc: Environment build took 1 minute 7 seconds"),
        Result(
            state=State.OK, notice="Suite piggyback: Environment build took 2 minutes 3 seconds"
        ),
    ]


def test_check_scheduler_rcc_setup_failures() -> None:
    assert list(
        _check_scheduler_status(
            section_robotmk_config=_CONFIG,
            section_robotmk_scheduler_phase=SchedulerPhase.Scheduling,
            section_robotmk_rcc_setup_failures=RCCSetupFailures(
                telemetry_disabling=["rcc"],
                long_path_support=[],
                shared_holotree=[],
                holotree_init=["piggyback"],
            ),
            section_robotmk_environment_build_states=EnvironmentBuildStates(
                root={
                    "system": EnvironmentBuildStatusNotNeeded.NotNeeded,
                }
            ),
            now=1,
        )
    ) == [
        Result(state=State.OK, summary="3 suites configured (system, rcc, piggyback)"),
        Result(
            state=State.OK,
            notice="Configuration of suite system\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: No\n- Maximum number of attempts: 1",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite rcc\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: Yes\n- Maximum number of attempts: 2",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite piggyback\n- Scheduling interval: 3 minutes 20 seconds\n- RCC: Yes\n- Maximum number of attempts: 1\n- Assigned to host: synth_mon_host",
        ),
        Result(state=State.OK, summary="Current phase: Suite scheduling"),
        Result(
            state=State.CRIT,
            summary="Disabling RCC telemetry failed for the following suites: rcc. These suites won't be scheduled.",
        ),
        Result(
            state=State.CRIT,
            summary="RCC holotree initialization failed for the following suites: piggyback. These suites won't be scheduled.",
        ),
    ]


def test_check_scheduler_status_environment_building_in_progress() -> None:
    assert list(
        _check_scheduler_status(
            section_robotmk_config=_CONFIG,
            section_robotmk_scheduler_phase=SchedulerPhase.EnvironmentBuilding,
            section_robotmk_rcc_setup_failures=RCCSetupFailures(
                telemetry_disabling=[],
                long_path_support=[],
                shared_holotree=[],
                holotree_init=[],
            ),
            section_robotmk_environment_build_states=EnvironmentBuildStates(
                root={
                    "system": EnvironmentBuildStatusNotNeeded.NotNeeded,
                    "rcc": EnvironmentBuildStatusInProgress(InProgress=1578),
                    "piggyback": EnvironmentBuildStatusSuccess(Success=123),
                }
            ),
            now=1656.123,
        )
    ) == [
        Result(state=State.OK, summary="3 suites configured (system, rcc, piggyback)"),
        Result(
            state=State.OK,
            notice="Configuration of suite system\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: No\n- Maximum number of attempts: 1",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite rcc\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: Yes\n- Maximum number of attempts: 2",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite piggyback\n- Scheduling interval: 3 minutes 20 seconds\n- RCC: Yes\n- Maximum number of attempts: 1\n- Assigned to host: synth_mon_host",
        ),
        Result(state=State.OK, summary="Current phase: Environment building"),
        Result(
            state=State.OK,
            summary="Suite rcc: Environment build currently running for 1 minute 18 seconds",
        ),
        Result(
            state=State.OK, notice="Suite piggyback: Environment build took 2 minutes 3 seconds"
        ),
    ]


def test_check_scheduler_status_environment_building_failures() -> None:
    assert list(
        _check_scheduler_status(
            section_robotmk_config=_CONFIG,
            section_robotmk_scheduler_phase=SchedulerPhase.Scheduling,
            section_robotmk_rcc_setup_failures=RCCSetupFailures(
                telemetry_disabling=[],
                long_path_support=[],
                shared_holotree=[],
                holotree_init=[],
            ),
            section_robotmk_environment_build_states=EnvironmentBuildStates(
                root={
                    "system": EnvironmentBuildStatusNotNeeded.NotNeeded,
                    "rcc": EnvironmentBuildStatusFailure(
                        Failure=EnvironmentBuildStatusErrorNonZeroExit.NonZeroExit
                    ),
                    "piggyback": EnvironmentBuildStatusFailure(
                        Failure=EnviromentBuildStatusErrorMessage(Error="RCC binary not found")
                    ),
                }
            ),
            now=1,
        )
    ) == [
        Result(state=State.OK, summary="3 suites configured (system, rcc, piggyback)"),
        Result(
            state=State.OK,
            notice="Configuration of suite system\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: No\n- Maximum number of attempts: 1",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite rcc\n- Scheduling interval: 10 minutes 0 seconds\n- RCC: Yes\n- Maximum number of attempts: 2",
        ),
        Result(
            state=State.OK,
            notice="Configuration of suite piggyback\n- Scheduling interval: 3 minutes 20 seconds\n- RCC: Yes\n- Maximum number of attempts: 1\n- Assigned to host: synth_mon_host",
        ),
        Result(state=State.OK, summary="Current phase: Suite scheduling"),
        Result(
            state=State.CRIT,
            summary="Suite rcc: Environment building failed. Suite won't be scheduled.",
        ),
        Result(
            state=State.CRIT,
            summary="Suite piggyback: Error while attempting to build environment, see service details. Suite won't be scheduled.",
            details="RCC binary not found",
        ),
    ]


def test_check_scheduler_status_config_error() -> None:
    assert list(
        _check_scheduler_status(
            section_robotmk_config=ConfigReadingError(
                ReadingError="Something went wrong.\nCould not read config file."
            ),
            section_robotmk_scheduler_phase=None,
            section_robotmk_rcc_setup_failures=None,
            section_robotmk_environment_build_states=None,
            now=1,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Error while reading configuration",
            details="Something went wrong.\nCould not read config file.",
        )
    ]


def test_check_scheduler_status_no_data() -> None:
    assert not list(
        _check_scheduler_status(
            section_robotmk_config=None,
            section_robotmk_scheduler_phase=None,
            section_robotmk_rcc_setup_failures=None,
            section_robotmk_environment_build_states=None,
            now=1,
        )
    )
