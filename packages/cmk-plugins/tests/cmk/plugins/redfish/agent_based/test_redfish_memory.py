#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_memory import (
    check_redfish_memory,
    discovery_redfish_memory,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_HEALTHY = {"Health": "OK", "State": "Enabled"}


def _dimm(dimm_id: str, **fields: object) -> dict[str, object]:
    return {
        "@odata.id": f"/redfish/v1/Systems/1/Memory/{dimm_id}",
        "@odata.type": "#Memory.v1_7_0.Memory",
        "Id": dimm_id,
        **fields,
    }


def _memory_section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [[json.dumps(entry)] for entry in entries]
    return parse_redfish_multiple(string_table)


def test_memory_modules_are_discovered_by_id() -> None:
    section = _memory_section(
        {
            "@odata.id": "/redfish/v1/Systems/1/Memory",
            "@odata.type": "#MemoryCollection.MemoryCollection",
            "Id": "Memory",
        },
        _dimm("proc1dimm1", Status=_HEALTHY),
    )

    assert list(discovery_redfish_memory(section)) == [Service(item="proc1dimm1")]


def test_absent_memory_modules_are_not_discovered() -> None:
    section = _memory_section(_dimm("proc1dimm2", Status={"State": "Absent"}))

    assert list(discovery_redfish_memory(section)) == []


def test_memory_module_properties_are_reported() -> None:
    section = _memory_section(
        _dimm(
            "proc1dimm1",
            CapacityMiB=32768,
            MemoryDeviceType="DDR4",
            OperatingSpeedMhz=3200,
            ErrorCorrection="MultiBitECC",
            Status=_HEALTHY,
        )
    )

    assert list(check_redfish_memory("proc1dimm1", section))[0] == Result(
        state=State.OK, summary="Size: 32GB, Type: DDR4-3200 MultiBitECC"
    )


def test_redfish_status_sets_the_memory_module_state() -> None:
    section = _memory_section(
        _dimm("proc1dimm1", CapacityMiB=32768, Status={"Health": "Warning", "State": "Enabled"})
    )

    assert list(check_redfish_memory("proc1dimm1", section))[-1] == Result(
        state=State.WARN,
        notice="Component State: A condition requires attention., This resource is enabled.",
    )


def test_memory_module_properties_fall_back_to_legacy_hpe_fields() -> None:
    section = _memory_section(
        _dimm(
            "proc1dimm1",
            SizeMB=16384,
            DIMMType="DDR4",
            MaximumFrequencyMHz=2933,
            ErrorCorrection="MultiBitECC",
            Status=_HEALTHY,
        )
    )

    assert list(check_redfish_memory("proc1dimm1", section))[0] == Result(
        state=State.OK, summary="Size: 16GB, Type: DDR4-2933 MultiBitECC"
    )


def test_hpe_dimm_status_sets_the_state_without_a_redfish_status() -> None:
    section = _memory_section(
        _dimm(
            "proc1dimm1",
            CapacityMiB=32768,
            Oem={"Hpe": {"DIMMStatus": "ConfigurationError"}},
        )
    )

    assert list(check_redfish_memory("proc1dimm1", section))[-1] == Result(
        state=State.CRIT, notice="Configuration error in DIMM."
    )


def test_unknown_hpe_dimm_status_is_unknown() -> None:
    section = _memory_section(
        _dimm("proc1dimm1", CapacityMiB=32768, Oem={"Hpe": {"DIMMStatus": "Exploded"}})
    )

    assert list(check_redfish_memory("proc1dimm1", section))[-1] == Result(
        state=State.UNKNOWN, notice="Unknown state"
    )


def test_memory_module_without_any_status_is_ok() -> None:
    section = _memory_section(_dimm("proc1dimm1", CapacityMiB=32768))

    assert list(check_redfish_memory("proc1dimm1", section))[-1] == Result(
        state=State.OK, notice="No known status value found"
    )


def test_vanished_memory_module_yields_no_result() -> None:
    section = _memory_section(_dimm("proc1dimm1", CapacityMiB=32768, Status=_HEALTHY))

    assert list(check_redfish_memory("proc1dimm2", section)) == []
