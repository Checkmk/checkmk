#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<hyperv_vm_ram:cached(1750083965,120)>>>
# config.hardware.RAMType Dynamic Memory
# config.hardware.StartRAM 4096
# config.hardware.MinRAM 512
# config.hardware.MaxRAM 1048576

from collections.abc import Mapping

from cmk.agent_based.v2 import Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_ram import check_hyperv_vm_ram


def test_check_hyperv_vm_ram_dynamic_memory():
    sample_section: Mapping[str, str] = {
        "config.hardware.RAMType": "Dynamic Memory",
        "config.hardware.StartRAM": "4096",
        "config.hardware.MinRAM": "512",
        "config.hardware.MaxRAM": "1048576",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="Dynamic Memory configured with 512 MB minimum and 1048576 MB maximum - start 4096 MB",
        )
    ]

    results = list(check_hyperv_vm_ram(sample_section))

    assert results == expected_result


def test_check_hyperv_vm_ram_no_data():
    sample_section: Mapping[str, str] = {}

    expected_result = [Result(state=State.UNKNOWN, summary="RAM information is missing")]

    results = list(check_hyperv_vm_ram(sample_section))

    assert results == expected_result


def test_check_hyperv_vm_ram_static_memory():
    sample_section: Mapping[str, str] = {
        "config.hardware.RAMType": "Static Memory",
        "config.hardware.RAM": "8192",
    }

    expected_result = [
        Result(
            state=State.OK,
            summary="Static Memory configured with 8192 MB",
        )
    ]

    results = list(check_hyperv_vm_ram(sample_section))

    assert results == expected_result
