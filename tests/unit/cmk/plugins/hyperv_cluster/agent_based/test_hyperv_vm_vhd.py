#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import PureWindowsPath

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_vhd import (
    check_hyperv_vm_vhd_dynamic,
    check_hyperv_vm_vhd_fixed,
    parse_hyperv_vm_vhd,
    VhdInfo,
    VhdType,
)


def test_parse_hyperv_vm_vhd_with_empty_string_table_raises_error() -> None:
    with pytest.raises(IndexError):
        parse_hyperv_vm_vhd([[]])


def test_parse_hyperv_vm_vhd_with_bad_string_returns_empty_section() -> None:
    results = parse_hyperv_vm_vhd([["bad", "bad"]])
    assert len(results) == 0


def test_parse_hyperv_vm_vhd_with_minimum_payload_parses_correctly() -> None:
    results = parse_hyperv_vm_vhd(
        [
            ["vhd", "1"],
            ["vhd.Name", "Test Name"],
            ["vhd.Type", "Dynamic"],
            ["vhd.Path", "c:\\VMs\\test.vhdx"],
            ["vhd.DiskSize", "2048"],
            ["vhd.FileSize", "1024"],
            ["vhd.controller.Type", "IDE"],
            ["vhd.controller.Number", "0"],
            ["vhd.controller.Location", "1"],
        ]
    )
    assert "IDE 0 1" in results
    assert results["IDE 0 1"].type == "Dynamic"
    assert results["IDE 0 1"].disk_size == 2048
    assert results["IDE 0 1"].file_size == 1024
    assert results["IDE 0 1"].main_path == PureWindowsPath("c:\\VMs\\test.vhdx")


def test_check_hyperv_vm_vhd_with_parsed_data_has_ok_result() -> None:
    file_size = 4
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=file_size,
            type=VhdType.DYNAMIC,
        )
    }
    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("absolute", ("no_levels", None))}, section
        )
    )
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK


def test_check_hyperv_vm_vhd_dynamic_with_parsed_data_and_no_levels_has_correct_state_and_summary() -> (
    None
):
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=4,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("absolute", ("no_levels", None))}, section
        )
    )

    assert Result(state=State.OK, summary="Disk name: test.vhd") in results
    assert Result(state=State.OK, summary="Current disk size: 1.56% - 4 B of 256 B") in results
    assert Result(state=State.OK, summary="VHD type: Dynamic") in results


def test_check_hyperv_vm_vhd_dynamic_with_safe_absolute_param_has_ok_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=64,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("absolute", ("fixed", (128, 192)))}, section
        )
    )

    assert Result(state=State.OK, summary="Current disk size: 25.00% - 64 B of 256 B") in results


def test_check_hyperv_vm_vhd_dynamic_with_warn_absolute_param_has_warning_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=192,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("absolute", ("fixed", (128, 256)))}, section
        )
    )

    assert Result(state=State.WARN, summary="Current disk size: 75.00% - 192 B of 256 B") in results


def test_check_hyperv_vm_vhd_dynamic_with_warn_absolute_param_has_crit_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=192,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("absolute", ("fixed", (64, 128)))}, section
        )
    )

    assert Result(state=State.CRIT, summary="Current disk size: 75.00% - 192 B of 256 B") in results


def test_check_hyperv_vm_vhd_dynamic_with_safe_relative_param_has_ok_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=192,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("relative", ("fixed", (76, 99)))}, section
        )
    )

    assert Result(state=State.OK, summary="Current disk size: 75.00% - 192 B of 256 B") in results


def test_check_hyperv_vm_vhd_dynamic_with_warn_relative_param_has_warning_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=192,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("relative", ("fixed", (65, 90)))}, section
        )
    )

    assert Result(state=State.WARN, summary="Current disk size: 75.00% - 192 B of 256 B") in results


def test_check_hyperv_vm_vhd_dynamic_with_warn_relative_param_has_crit_state() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=192,
            type=VhdType.DYNAMIC,
        )
    }

    results = list(
        check_hyperv_vm_vhd_dynamic(
            "Test Service", {"size_limit": ("relative", ("fixed", (30, 60)))}, section
        )
    )

    assert Result(state=State.CRIT, summary="Current disk size: 75.00% - 192 B of 256 B") in results


def test_check_hyperv_vm_vhd_fixed_with_parsed_data_correct_state_and_summary() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=256,
            type=VhdType.FIXED,
        )
    }

    results = list(check_hyperv_vm_vhd_fixed("Test Service", section))

    assert Result(state=State.OK, summary="Disk name: test.vhd") in results
    assert Result(state=State.OK, summary="Maximum disk size: 256 B") in results
    assert Result(state=State.OK, summary="VHD type: Fixed") in results


def test_check_hyperv_vm_vhd_fixed_with_stored_data_has_size_metric() -> None:
    section = {
        "Test Service": VhdInfo(
            main_path=PureWindowsPath("C:\\Test\\test.vhd"),
            disk_size=256,
            file_size=256,
            type=VhdType.FIXED,
        )
    }

    results = list(check_hyperv_vm_vhd_fixed("Test Service", section))

    assert Metric("hyperv_vhd_metrics_disk_size", 256.0) in results
