#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent:
# <<<hyperv_vm_ram:cached(1750083965,120)>>>
# config.hardware.RAMType dynamic
# config.hardware.AssignedRAM 4294967296
# config.hardware.StartRAM 2147483648
# config.hardware.MinRAM 1073741824
# config.hardware.MaxRAM 4294967296

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_ram import (
    check_hyperv_vm_ram,
    parse_hyperv_vm_ram,
    Section,
)


def mb_to_kb(a: int) -> int:
    return a * 1024**2


def test_parse_hyperv_vm_ram_with_empty_string_table_raises_error():
    with pytest.raises(IndexError):
        parse_hyperv_vm_ram([[]])


def test_parse_hyperv_vm_ram_with_bad_string_table_raises_error():
    with pytest.raises(KeyError):
        parse_hyperv_vm_ram([["bad", "bad"]])


def test_parse_hyperv_vm_ram_with_minimum_payload_parses_correctly():
    result = parse_hyperv_vm_ram([["config.hardware.AssignedRAM", "1024"]])
    assert result.assigned_ram == 1024


def test_parse_hyperv_vm_ram_without_payload_type_is_dynamic_not_set():
    result = parse_hyperv_vm_ram([["config.hardware.AssignedRAM", "1024"]])
    assert not result.is_dynamic


def test_parse_hyperv_vm_ram_with_static_payload_type_is_dynamic_not_set():
    result = parse_hyperv_vm_ram(
        [["config.hardware.AssignedRAM", "1024"], ["config.hardware.RAMType", "static"]]
    )
    assert not result.is_dynamic


def test_parse_hyperv_vm_ram_with_dynamic_payload_type_is_dynamic_set():
    result = parse_hyperv_vm_ram(
        [["config.hardware.AssignedRAM", "1024"], ["config.hardware.RAMType", "dynamic"]]
    )
    assert result.is_dynamic


def test_parse_hyperv_vm_ram_with_complete_payload_parses_correctly():
    result = parse_hyperv_vm_ram(
        [
            ["config.hardware.AssignedRAM", "1024"],
            ["config.hardware.RAMDemand", "512"],
            ["config.hardware.StartRAM", "128"],
            ["config.hardware.MinRAM", "64"],
            ["config.hardware.MaxRAM", "2048"],
            ["config.hardware.RAMType", "dynamic"],
        ]
    )

    assert result.assigned_ram == 1024
    assert result.start_ram == 128
    assert result.min_ram == 64
    assert result.max_ram == 2048
    assert result.ram_demand == 512
    assert result.is_dynamic


def test_check_hyperv_vm_ram_with_demand_has_correct_state_and_summary():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(4096),
        ram_demand=mb_to_kb(4096),
        start_ram=0,
        max_ram=0,
        min_ram=0,
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Current RAM: 4.00 GiB") in results
    assert Result(state=State.OK, summary="Demand: 4.00 GiB") in results


def test_check_hyperv_vm_ram_without_demand_memory_has_correct_current_and_no_demand_value():
    sample_section = Section(
        is_dynamic=False,
        assigned_ram=mb_to_kb(1024),
        ram_demand=0,
        start_ram=0,
        max_ram=0,
        min_ram=0,
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Current RAM: 1.00 GiB") in results
    demand = next(
        (i for i in results if isinstance(i, Result) and i.summary.startswith("Demand")), None
    )
    assert demand is None


def test_check_hyperv_vm_ram_has_correct_details():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(4096),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8912),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Current RAM: 4.00 GiB") in results
    assert Result(state=State.OK, summary="Demand: 1.00 GiB") in results
    assert Result(state=State.OK, notice="Start RAM: 512 MiB") in results
    assert Result(state=State.OK, notice="Min RAM: 128 MiB") in results
    assert Result(state=State.OK, notice="Dynamic memory Enabled: True") in results


def test_check_hyperv_vm_ram_is_ok_when_no_rules_configured():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(4096),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8912),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Current RAM: 4.00 GiB") in results


def test_check_hyperv_vm_ram_is_crit_when_current_ram_above_crit_percentage():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(4096),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("fixed", (30, 49)), "check_demand": False},
            sample_section,
        )
    )

    assert (
        Result(state=State.CRIT, summary="Current RAM: 4.00 GiB (warn/crit at 2.40 GiB/3.92 GiB)")
        in results
    )


def test_check_hyperv_vm_ram_is_warn_when_current_ram_above_warn_percentage():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(4096),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("fixed", (49, 80)), "check_demand": False},
            sample_section,
        )
    )

    assert (
        Result(state=State.WARN, summary="Current RAM: 4.00 GiB (warn/crit at 3.92 GiB/6.40 GiB)")
        in results
    )


def test_check_hyperv_vm_ram_is_crit_when_current_ram_below_warn_percentage():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(63),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("fixed", (50, 25)), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert (
        Result(
            state=State.WARN, summary="Current RAM: 63.0 MiB (warn/crit below 64.0 MiB/32.0 MiB)"
        )
        in results
    )


def test_check_hyperv_vm_ram_is_crit_when_current_ram_below_crit_percentage():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(31),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("fixed", (50, 25)), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert (
        Result(
            state=State.CRIT, summary="Current RAM: 31.0 MiB (warn/crit below 64.0 MiB/32.0 MiB)"
        )
        in results
    )


def test_check_hyperv_vm_ram_state_is_ok_when_demand_check_is_disabled():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(31),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": False},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Demand: 1.00 GiB") in results


def test_check_hyperv_vm_ram_state_is_ok_when_demand_check_is_enabled_and_demand_is_lower():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(2048),
        ram_demand=mb_to_kb(1024),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": True},
            sample_section,
        )
    )

    assert Result(state=State.OK, summary="Demand: 1.00 GiB") in results


def test_check_hyperv_vm_ram_state_is_warn_when_demand_check_is_enabled_and_demand_is_higher():
    sample_section = Section(
        is_dynamic=True,
        assigned_ram=mb_to_kb(2048),
        ram_demand=mb_to_kb(2096),
        start_ram=mb_to_kb(512),
        max_ram=mb_to_kb(8192),
        min_ram=mb_to_kb(128),
    )
    results = list(
        check_hyperv_vm_ram(
            {"min_ram": ("no_levels", None), "max_ram": ("no_levels", None), "check_demand": True},
            sample_section,
        )
    )

    assert Result(state=State.WARN, summary="Demand: 2.05 GiB") in results
