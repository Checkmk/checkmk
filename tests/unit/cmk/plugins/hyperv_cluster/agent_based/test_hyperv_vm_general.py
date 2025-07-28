#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_general import (
    check_hyperv_vm_general_name,
    check_hyperv_vm_general_running_on,
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


def test_check_hyperv_vm_general_name() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.vmid": "ec17fbba-428a-41b0-9d38-1ca689aeb919",
    }

    expected_result = [Result(state=State.OK, summary="Server25")]

    results = list(check_hyperv_vm_general_name(sample_section))

    assert results == expected_result


def test_check_hyperv_vm_general_name_no_data() -> None:
    sample_section = {
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.vmid": "ec17fbba-428a-41b0-9d38-1ca689aeb919",
    }

    expected_result = [Result(state=State.UNKNOWN, summary="Name information is missing")]

    results = list(check_hyperv_vm_general_name(sample_section))

    assert results == expected_result


def test_check_hyperv_vm_general_running_on() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.host": "WIN-LBC2PSOUUG1",
        "runtime.powerState": "Running",
        "config.vmid": "ec17fbba-428a-41b0-9d38-1ca689aeb919",
    }

    expected_result = [
        Result(state=State.OK, summary="Running on WIN-LBC2PSOUUG1 with state Running")
    ]

    results = list(check_hyperv_vm_general_running_on(sample_section))

    assert results == expected_result


def test_check_hyperv_vm_general_running_on_no_data() -> None:
    sample_section = {
        "name": "Server25",
        "runtime.powerState": "Running",
        "config.vmid": "ec17fbba-428a-41b0-9d38-1ca689aeb919",
    }

    expected_result = [Result(state=State.UNKNOWN, summary="Runtime host information is missing")]

    results = list(check_hyperv_vm_general_running_on(sample_section))

    assert results == expected_result
