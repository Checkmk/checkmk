#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_general import (
    check_hyperv_vm_general,
    GeneralParams,
    hyperv_vm_general_default_params,
)

# Example output from agent:
# <<<hyperv_vm_general:cached(1750083965,120)>>>
# name Server25
# cluster.clustered False
# runtime.host WIN-LBC2PSOUUG1
# runtime.powerState Running
# runtime.operationState Operating normally
# config.vmid ec17fbba-428a-41b0-9d38-1ca689aeb919
# config.generation 2
# config.version 10.0
# config.created 6/10/2025 5:34:48 PM
# config.MemberOfVMGroups 0
# guest.fqdn WIN-PA6LHI11TL6
# guest.os Windows Server 2025 Standard Evaluation
# guest.IntegrationServicesVersion 10.0.26100
# guest.IntegrationServicesState
# config.AutomaticStopAction Save
# config.AutomaticStartAction StartIfRunning
# config.AutomaticStartDelay 0
# config.ConfigurationPath E:\Server25
# config.CheckpointPath E:\Server25
# config.CurrentCheckpointType Production
# replication.mode not configured
# access nobody
# security.shieldedVM False
# security.TPMEnabled False
# security.KeyStorageDriveEnabled False
# security.StateMigrationEncrypted False


def test_check_hyperv_vm_general_running_ok() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.generation": "2",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.OK,
            summary="State: Running",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.OK,
            summary="VM Generation: 2",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_off_critical() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Off",
        "config.generation": "2",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.CRIT,
            summary="State: Off",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.OK,
            summary="VM Generation: 2",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_paused_warning() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Paused",
        "config.generation": "2",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.WARN,
            summary="State: Paused",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.OK,
            summary="VM Generation: 2",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_wrong_generation() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.generation": "1",  # Default expects generation 2
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.OK,
            summary="State: Running",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.WARN,
            summary="VM Generation: 1",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_wrong_state_and_generation() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Off",
        "config.generation": "1",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.CRIT,
            summary="State: Off",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.WARN,
            summary="VM Generation: 1",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_no_name() -> None:
    sample_section = {
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.generation": "2",
    }

    expected_result = [Result(state=State.WARN, summary="VM name information is missing")]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_unknown_power_state() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Suspended",  # Not in default mapping
        "config.generation": "2",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.UNKNOWN,
            summary="State: Suspended",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.OK,
            summary="VM Generation: 2",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_missing_data() -> None:
    sample_section = {
        "name": "Server25",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.WARN,
            summary="State information is missing",
        ),
        Result(
            state=State.WARN,
            summary="Host information is missing",
        ),
        Result(
            state=State.WARN,
            summary="VM Generation information is missing",
        ),
    ]

    results = list(check_hyperv_vm_general(hyperv_vm_general_default_params, sample_section))
    assert results == expected_result


def test_check_hyperv_vm_general_custom_params() -> None:
    custom_params: GeneralParams = {
        "power_state": {
            "running": State.WARN.value,  # Custom: running is WARN instead of OK
            "off": State.OK.value,  # Custom: off is OK instead of CRIT
        },
        "vm_generation": {
            "expected_generation": "generation_1",  # Custom: expect generation 1
            "state_if_not_expected": State.CRIT.value,  # Custom: CRIT instead of WARN
        },
    }

    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.generation": "2",  # Wrong generation according to custom params
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="VM name: Server25",
        ),
        Result(
            state=State.WARN,
            summary="State: Running",
        ),
        Result(
            state=State.OK,
            summary="Host: WIN-LBC2PSOUUG1",
        ),
        Result(
            state=State.CRIT,
            summary="VM Generation: 2",
        ),
    ]

    results = list(check_hyperv_vm_general(custom_params, sample_section))
    assert results == expected_result
