#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.smart.agent_based.smart_ata import _check_smart_ata, discover_smart_ata
from cmk.plugins.smart.agent_based.smart_posix import (
    ATAAll,
    ATADevice,
    ATARawValue,
    ATATable,
    ATATableEntry,
    parse_smart_posix_all,
    Temperature,
)

STRING_TABLE_ATA = [
    [  # removed keys ata_smart_data and ata_smart_selective_self_test_log, modified serial number and ata_smart_attributes
        '{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.1.0-26-amd64","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda"],"drive_database_version":{"string":"7.3/5319"},"exit_status":128},"local_time":{"time_t":1728840886,"asctime":"Sun Oct 13 19:34:46 2024 CEST"},"device":{"name":"/dev/sda","info_name":"/dev/sda [SAT]","type":"sat","protocol":"ATA"},"model_family":"Western Digital AV","model_name":"WDC WD3200BUCT-63TWBY0","serial_number":"XXXATA","wwn":{"naa":5,"oui":5358,"id":27262891493},"firmware_version":"01.01A02","user_capacity":{"blocks":625142448,"bytes":320072933376},"logical_block_size":512,"physical_block_size":4096,"rotation_rate":5400,"trim":{"supported":false},"in_smartctl_database":true,"ata_version":{"string":"ATA8-ACS (minor revision not indicated)","major_value":510,"minor_value":0},"sata_version":{"string":"SATA 2.6","value":30},"interface_speed":{"max":{"sata_value":6,"string":"3.0 Gb/s","units_per_second":30,"bits_per_unit":100000000}},"smart_support":{"available":true,"enabled":true},"smart_status":{"passed":true},"ata_sct_capabilities":{"value":28725,"error_recovery_control_supported":false,"feature_control_supported":true,"data_table_supported":true},"ata_smart_attributes":{"revision":16,"table":[{"id":1,"name":"Raw_Read_Error_Rate","value":200,"worst":200,"thresh":51,"when_failed":"","flags":{"value":47,"string":"POSR-K ","prefailure":true,"updated_online":true,"performance":true,"error_rate":true,"event_count":false,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":5,"name":"Reallocated_Sector_Ct","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":51,"string":"PO--CK ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":9,"name":"Power_On_Hours","value":97,"worst":97,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":2901,"string":"2901"}},{"id":10,"name":"Spin_Retry_Count","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":12,"name":"Power_Cycle_Count","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":669,"string":"669"}},{"id":194,"name":"Temperature_Celsius","value":105,"worst":95,"thresh":0,"when_failed":"","flags":{"value":34,"string":"-O---K ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":false,"auto_keep":true},"raw":{"value":38,"string":"38"}},{"id":196,"name":"Reallocated_Event_Count","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":197,"name":"Current_Pending_Sector","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":199,"name":"UDMA_CRC_Error_Count","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}}]},"power_on_time":{"hours":2901},"power_cycle_count":669,"temperature":{"current":38},"ata_smart_error_log":{"summary":{"revision":1,"count":0}},"ata_smart_self_test_log":{"standard":{"revision":1,"table":[{"type":{"value":2,"string":"Extended offline"},"status":{"value":116,"string":"Completed: read failure","remaining_percent":40,"passed":false},"lifetime_hours":6,"lba":365037392}],"count":1,"error_count_total":1,"error_count_outdated":0}}}'
    ],
]

SECTION_ATA = [
    ATAAll(
        device=ATADevice(protocol="ATA", name="/dev/sda"),
        ata_smart_attributes=ATATable(
            table=[
                ATATableEntry(
                    id=1, name="Raw_Read_Error_Rate", value=200, thresh=51, raw=ATARawValue(value=0)
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
                    id=10, name="Spin_Retry_Count", value=100, thresh=0, raw=ATARawValue(value=0)
                ),
                ATATableEntry(
                    id=12, name="Power_Cycle_Count", value=100, thresh=0, raw=ATARawValue(value=669)
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
]


def test_parse_smart_ata() -> None:
    section = parse_smart_posix_all(STRING_TABLE_ATA)
    assert section == SECTION_ATA


def test_discover_smart_ata_stat() -> None:
    assert list(discover_smart_ata(SECTION_ATA)) == [
        Service(item="/dev/sda", parameters={"5": 0, "10": 0, "197": 0, "199": 0}),
    ]


def test_check_smart_ata_stat() -> None:
    assert list(
        _check_smart_ata("/dev/sda", {"5": 0, "10": 0, "197": 0, "199": 0}, SECTION_ATA, {}, 0)
    ) == [
        Result(state=State.OK, summary="Reallocated sectors: 0"),
        Metric("harddrive_reallocated_sectors", 0.0),
        Result(state=State.OK, summary="Powered on: 48 minutes 21 seconds"),
        Metric("uptime", 2901.0),
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
