#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    GetRateError,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.plugins.smart.agent_based.smart_ata import (
    _check_command_timeout,
    _check_smart_ata,
    AtaParams,
    DEFAULT_PARAMS,
    discover_smart_ata,
)
from cmk.plugins.smart.agent_based.smart_posix import (
    ATAAll,
    ATADevice,
    ATARawValue,
    ATATable,
    ATATableEntry,
    parse_smart_posix,
    SCSIAll,
    SCSIDevice,
    Section,
    Temperature,
)

STRING_TABLE_ATA = [
    [  # removed keys ata_smart_data and ata_smart_selective_self_test_log, modified serial number and ata_smart_attributes
        '{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.1.0-26-amd64","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda"],"drive_database_version":{"string":"7.3/5319"},"exit_status":128},"local_time":{"time_t":1728840886,"asctime":"Sun Oct 13 19:34:46 2024 CEST"},"device":{"name":"/dev/sda","info_name":"/dev/sda [SAT]","type":"sat","protocol":"ATA"},"model_family":"Western Digital AV","model_name":"WDC WD3200BUCT-63TWBY0","serial_number":"XXXATA","wwn":{"naa":5,"oui":5358,"id":27262891493},"firmware_version":"01.01A02","user_capacity":{"blocks":625142448,"bytes":320072933376},"logical_block_size":512,"physical_block_size":4096,"rotation_rate":5400,"trim":{"supported":false},"in_smartctl_database":true,"ata_version":{"string":"ATA8-ACS (minor revision not indicated)","major_value":510,"minor_value":0},"sata_version":{"string":"SATA 2.6","value":30},"interface_speed":{"max":{"sata_value":6,"string":"3.0 Gb/s","units_per_second":30,"bits_per_unit":100000000}},"smart_support":{"available":true,"enabled":true},"smart_status":{"passed":true},"ata_sct_capabilities":{"value":28725,"error_recovery_control_supported":false,"feature_control_supported":true,"data_table_supported":true},"ata_smart_attributes":{"revision":16,"table":[{"id":1,"name":"Raw_Read_Error_Rate","value":200,"worst":200,"thresh":51,"when_failed":"","flags":{"value":47,"string":"POSR-K ","prefailure":true,"updated_online":true,"performance":true,"error_rate":true,"event_count":false,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":5,"name":"Reallocated_Sector_Ct","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":51,"string":"PO--CK ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":9,"name":"Power_On_Hours","value":97,"worst":97,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":2901,"string":"2901"}},{"id":10,"name":"Spin_Retry_Count","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":12,"name":"Power_Cycle_Count","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":669,"string":"669"}},{"id":194,"name":"Temperature_Celsius","value":105,"worst":95,"thresh":0,"when_failed":"","flags":{"value":34,"string":"-O---K ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":false,"auto_keep":true},"raw":{"value":38,"string":"38"}},{"id":196,"name":"Reallocated_Event_Count","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":197,"name":"Current_Pending_Sector","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":199,"name":"UDMA_CRC_Error_Count","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}}]},"power_on_time":{"hours":2901},"power_cycle_count":669,"temperature":{"current":38},"ata_smart_error_log":{"summary":{"revision":1,"count":0}},"ata_smart_self_test_log":{"standard":{"revision":1,"table":[{"type":{"value":2,"string":"Extended offline"},"status":{"value":116,"string":"Completed: read failure","remaining_percent":40,"passed":false},"lifetime_hours":6,"lba":365037392}],"count":1,"error_count_total":1,"error_count_outdated":0}}}'
    ],
]

SECTION_ATA = Section(
    devices={
        "WDC WD3200BUCT-63TWBY0 XXXATA": ATAAll(
            device=ATADevice(protocol="ATA", name="/dev/sda"),
            model_name="WDC WD3200BUCT-63TWBY0",
            serial_number="XXXATA",
            ata_smart_attributes=ATATable(
                table=[
                    ATATableEntry(
                        id=1,
                        name="Raw_Read_Error_Rate",
                        value=200,
                        thresh=51,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=5,
                        name="Reallocated_Sector_Ct",
                        value=200,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=9, name="Power_On_Hours", value=97, thresh=0, raw=ATARawValue(value=2901)
                    ),
                    ATATableEntry(
                        id=10,
                        name="Spin_Retry_Count",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=12,
                        name="Power_Cycle_Count",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=669),
                    ),
                    ATATableEntry(
                        id=194,
                        name="Temperature_Celsius",
                        value=105,
                        thresh=0,
                        raw=ATARawValue(value=38),
                    ),
                    ATATableEntry(
                        id=196,
                        name="Reallocated_Event_Count",
                        value=200,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=197,
                        name="Current_Pending_Sector",
                        value=200,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=199,
                        name="UDMA_CRC_Error_Count",
                        value=200,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                ]
            ),
            temperature=Temperature(current=38),
        )
    },
    failures=[],
)

SECTION_SCAN_ARG = Section(
    devices={
        "WDC WD3200BUCT-63TWBY0 XXXATA": SCSIAll(
            device=SCSIDevice(protocol="SCSI", name="/dev/sda"),
            model_name="WDC WD3200BUCT-63TWBY0",
            serial_number="XXXATA",
            temperature=Temperature(current=0),
        ),
    },
    failures=[],
)


def test_parse_smart_ata() -> None:
    section = parse_smart_posix(STRING_TABLE_ATA)
    assert section == SECTION_ATA


def test_discover_smart_ata_stat() -> None:
    assert list(
        discover_smart_ata(
            SECTION_ATA,
            SECTION_SCAN_ARG,
        )
    ) == [
        Service(
            item="WDC WD3200BUCT-63TWBY0 XXXATA",
            labels=[
                ServiceLabel("cmk/smart/type", "ATA"),
                ServiceLabel("cmk/smart/device", "/dev/sda"),
                ServiceLabel("cmk/smart/model", "WDC WD3200BUCT-63TWBY0"),
                ServiceLabel("cmk/smart/serial", "XXXATA"),
            ],
            parameters={
                "id_5": 0,
                "id_10": 0,
                "id_184": None,
                "id_187": None,
                "id_188": None,
                "id_196": 0,
                "id_197": 0,
                "id_199": 0,
            },
        ),
    ]


def test_check_smart_ata_stat() -> None:
    ata_params: AtaParams = DEFAULT_PARAMS | {  # type: ignore[assignment]
        "id_5": 0,
        "id_10": 0,
        "id_184": None,
        "id_187": None,
        "id_188": None,
        "id_196": 0,
        "id_197": 0,
        "id_199": 0,
    }
    assert list(
        _check_smart_ata(
            "WDC WD3200BUCT-63TWBY0 XXXATA",
            ata_params,
            SECTION_ATA,
            SECTION_SCAN_ARG,
            {},
            0,
        )
    ) == [
        Result(state=State.OK, summary="Reallocated sectors: 0"),
        Metric("harddrive_reallocated_sectors", 0.0),
        Result(state=State.OK, summary="Powered on: 120 days 21 hours"),
        Metric("uptime", 10443600.0),
        Result(state=State.OK, summary="Spin retries: 0"),
        Metric("harddrive_spin_retries", 0.0),
        Result(state=State.OK, summary="Power cycles: 669"),
        Metric("harddrive_power_cycles", 669.0),
        Result(state=State.OK, summary="Reallocated events: 0"),
        Metric("harddrive_reallocated_events", 0.0),
        Result(state=State.OK, summary="Normalized value: 200.00"),
        Result(state=State.OK, summary="Pending sectors: 0"),
        Metric("harddrive_pending_sectors", 0.0),
        Result(state=State.OK, summary="UDMA CRC errors: 0"),
        Metric("harddrive_udma_crc_errors", 0.0),
    ]


def test_check_command_timeout() -> None:
    # Real life example
    # {"id":188,"name":"Command_Timeout","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":92,"string":"92"}}
    disk = ATAAll(
        device=ATADevice(protocol="ATA", name="/dev/sda"),
        model_name="WDC WD3200BUCT-63TWBY0",
        serial_number="XXXATA",
        ata_smart_attributes=ATATable(
            table=[
                ATATableEntry(
                    id=188,
                    name="Command_Timeout",
                    value=100,
                    thresh=0,
                    raw=ATARawValue(value=92),
                ),
            ]
        ),
        temperature=Temperature(current=38),
    )
    value_store: dict[str, object] = {}
    with pytest.raises(GetRateError):
        _check_results = list(_check_command_timeout(disk, value_store, 1.0)) == []
    assert list(_check_command_timeout(disk, value_store, 2.0)) == [
        Result(state=State.OK, summary="Command Timeout Counter: 92"),
        Metric("harddrive_cmd_timeouts", 92.0),
    ]


def test_check_command_timeout_critical() -> None:
    disk = ATAAll(
        device=ATADevice(protocol="ATA", name="/dev/sda"),
        model_name="WDC WD3200BUCT-63TWBY0",
        serial_number="XXXATA",
        ata_smart_attributes=ATATable(
            table=[
                ATATableEntry(
                    id=188,
                    name="Command_Timeout",
                    value=100,
                    thresh=0,
                    raw=ATARawValue(value=92),
                ),
            ]
        ),
        temperature=Temperature(current=38),
    )
    disk_second = ATAAll(
        model_name="WDC WD3200BUCT-63TWBY0",
        serial_number="XXXATA",
        device=ATADevice(protocol="ATA", name="/dev/sda"),
        ata_smart_attributes=ATATable(
            table=[
                ATATableEntry(
                    id=188,
                    name="Command_Timeout",
                    value=100,
                    thresh=0,
                    raw=ATARawValue(value=94),
                ),
            ]
        ),
        temperature=Temperature(current=38),
    )
    value_store: dict[str, object] = {}
    with pytest.raises(GetRateError):
        _check_results = list(_check_command_timeout(disk, value_store, 1.0)) == []
    assert list(_check_command_timeout(disk_second, value_store, 2.0)) == [
        Result(
            state=State.CRIT,
            summary="Command Timeout Counter: 94 (counter increased more than 100 counts / h (!!))",
        ),
        Metric("harddrive_cmd_timeouts", 94.0),
    ]


def test_check_smart_ata_configured() -> None:
    services = list(
        discover_smart_ata(
            SECTION_ATA,
            SECTION_SCAN_ARG,
        )
    )
    service = services[0]
    assert service.item is not None
    params = {
        "levels_5": ("levels_upper", ("fixed", (0, 1))),
        "levels_10": ("levels_upper", ("fixed", (0, 1))),
        "levels_184": ("levels_upper", ("fixed", (0, 1))),
        "levels_187": ("levels_upper", ("fixed", (0, 1))),
        "levels_196": ("levels_upper", ("fixed", (0, 1))),
        "levels_197": ("levels_upper", ("fixed", (0, 1))),
        "levels_199": ("levels_upper", ("fixed", (0, 1))),
    }
    ata_params: AtaParams = dict(service.parameters) | DEFAULT_PARAMS | params  # type: ignore[assignment]

    check_results = list(
        _check_smart_ata(service.item, ata_params, SECTION_ATA, SECTION_SCAN_ARG, {}, 0)
    )

    assert check_results == [
        Result(state=State.WARN, summary="Reallocated sectors: 0 (warn/crit at 0/1)"),
        Metric("harddrive_reallocated_sectors", 0.0, levels=(0.0, 1.0)),
        Result(state=State.OK, summary="Powered on: 120 days 21 hours"),
        Metric("uptime", 10443600.0),
        Result(state=State.WARN, summary="Spin retries: 0 (warn/crit at 0/1)"),
        Metric("harddrive_spin_retries", 0.0, levels=(0.0, 1.0)),
        Result(state=State.OK, summary="Power cycles: 669"),
        Metric("harddrive_power_cycles", 669.0),
        Result(state=State.WARN, summary="Reallocated events: 0 (warn/crit at 0/1)"),
        Metric("harddrive_reallocated_events", 0.0, levels=(0.0, 1.0)),
        Result(state=State.OK, summary="Normalized value: 200.00"),
        Result(state=State.WARN, summary="Pending sectors: 0 (warn/crit at 0/1)"),
        Metric("harddrive_pending_sectors", 0.0, levels=(0.0, 1.0)),
        Result(state=State.WARN, summary="UDMA CRC errors: 0 (warn/crit at 0/1)"),
        Metric("harddrive_udma_crc_errors", 0.0, levels=(0.0, 1.0)),
    ]
