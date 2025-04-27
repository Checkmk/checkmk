#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.smart.agent_based.smart_posix import (
    ATAAll,
    ATADevice,
    ATARawValue,
    ATATable,
    ATATableEntry,
    CantOpenDevice,
    FailureAll,
    parse_smart_posix,
    SCSIAll,
    SCSIDevice,
    SCSITemperature,
    Section,
    SmartctlError,
    Temperature,
)
from cmk.plugins.smart.agent_based.smart_scsi import discovery_smart_scsi_temp

SMART_POSIX_ALL = [
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda"],"messages":[{"string":"Smartctl open device: /dev/sda failed: DELL or MegaRaid controller, please try adding '-d megaraid,N'","severity":"error"}],"exit_status":2},"local_time":{"time_t":1740483986,"asctime":"Tue Feb 25 11:46:26 2025 GMT"}}"""
    ],
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdb"],"drive_database_version":{"string":"7.3/5319"},"exit_status":4},"local_time":{"time_t":1740483986,"asctime":"Tue Feb 25 11:46:26 2025 GMT"},"device":{"name":"/dev/sdb","info_name":"/dev/sdb [SAT]","type":"sat","protocol":"ATA"},"model_name":"DELLBOSS VD","serial_number":"dd8b62ae0b480010","firmware_version":"MV.R00-0","user_capacity":{"blocks":468731008,"bytes":239990276096},"logical_block_size":512,"physical_block_size":4096,"trim":{"supported":true,"deterministic":false,"zeroed":false},"in_smartctl_database":false,"ata_version":{"string":"ATA8-ACS, ATA/ATAPI-7 T13/1532D revision 4a","major_value":510,"minor_value":33},"smart_support":{"available":false}}"""
    ],
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/bus/0"],"messages":[{"string":"/dev/bus/0: Unable to detect device type","severity":"error"}],"exit_status":1},"local_time":{"time_t":1740483986,"asctime":"Tue Feb 25 11:46:26 2025 GMT"}}"""
    ],
]

SECTION_SMART_POSIX_ALL = Section(
    devices={
        "DELLBOSS VD dd8b62ae0b480010": ATAAll(
            device=ATADevice(protocol="ATA", name="/dev/sdb"),
            model_name="DELLBOSS VD",
            serial_number="dd8b62ae0b480010",
            ata_smart_attributes=None,
            temperature=None,
        )
    },
    failures=[FailureAll(device=None), FailureAll(device=None)],
)


def test_parse_smart_posix() -> None:
    assert parse_smart_posix(SMART_POSIX_ALL) == SECTION_SMART_POSIX_ALL


SMART_POSIX_SCAN_ARG = [
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda","-d","scsi"],"exit_status":4},"local_time":{"time_t":1740485276,"asctime":"Tue Feb 25 12:07:56 2025 GMT"},"device":{"name":"/dev/sda","info_name":"/dev/sda","type":"scsi","protocol":"SCSI"},"scsi_vendor":"DELL","scsi_product":"PERC H740P Mini","scsi_model_name":"DELL PERC H740P Mini","scsi_revision":"5.13","scsi_version":"SPC-3","user_capacity":{"blocks":22496673792,"bytes":11518296981504},"logical_block_size":512,"rotation_rate":0,"logical_unit_id":"0x62cea7f069f4f4002cdd61b0b23cf598","serial_number":"0098f53cb2b061dd2c00f4f469f0a7ce","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":false},"temperature":{"current":0},"scsi_temperature":{"drive_trip":0}}"""
    ],
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdb","-d","scsi"],"exit_status":4},"local_time":{"time_t":1740485276,"asctime":"Tue Feb 25 12:07:56 2025 GMT"},"device":{"name":"/dev/sdb","info_name":"/dev/sdb","type":"scsi","protocol":"SCSI"},"user_capacity":{"blocks":468731008,"bytes":239990276096},"logical_block_size":512,"physical_block_size":4096,"scsi_lb_provisioning":{"name":"not reported","value":0,"management_enabled":{"name":"LBPME","value":1},"read_zeros":{"name":"LBPRZ","value":0}},"rotation_rate":0,"serial_number":"dd8b62ae0b480010","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":false},"temperature":{"current":0},"scsi_temperature":{"drive_trip":0}}"""
    ],
    [
        """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/bus/0","-d","megaraid,0"],"drive_database_version":{"string":"7.3/5319"},"messages":[{"string":"Warning: This result is based on an Attribute check.","severity":"warning"}],"exit_status":0},"local_time":{"time_t":1740485276,"asctime":"Tue Feb 25 12:07:56 2025 GMT"},"device":{"name":"/dev/bus/0","info_name":"/dev/bus/0 [megaraid_disk_00] [SAT]","type":"sat+megaraid,0","protocol":"ATA"},"model_name":"SAMSUNG MZ7L31T9HBLT-00A07","serial_number":"S6ESNC0W622008","wwn":{"naa":5,"oui":9528,"id":66360213316},"firmware_version":"JXTC304Q","user_capacity":{"blocks":3750748848,"bytes":1920383410176},"logical_block_size":512,"physical_block_size":4096,"rotation_rate":0,"form_factor":{"ata_value":3,"name":"2.5 inches"},"trim":{"supported":true,"deterministic":true,"zeroed":true},"in_smartctl_database":false,"ata_version":{"string":"ACS-4 T13/BSR INCITS 529 revision 5","major_value":4092,"minor_value":94},"sata_version":{"string":"SATA 3.2","value":255},"interface_speed":{"max":{"sata_value":14,"string":"6.0 Gb/s","units_per_second":60,"bits_per_unit":100000000},"current":{"sata_value":3,"string":"6.0 Gb/s","units_per_second":60,"bits_per_unit":100000000}},"smart_support":{"available":true,"enabled":true},"smart_status":{"passed":true},"ata_smart_data":{"offline_data_collection":{"status":{"value":0,"string":"was never started"},"completion_seconds":0},"self_test":{"status":{"value":0,"string":"completed without error","passed":true},"polling_minutes":{"short":2,"extended":100}},"capabilities":{"values":[83,3],"exec_offline_immediate_supported":true,"offline_is_aborted_upon_new_cmd":false,"offline_surface_scan_supported":false,"self_tests_supported":true,"conveyance_self_test_supported":false,"selective_self_test_supported":true,"attribute_autosave_enabled":true,"error_logging_supported":true,"gp_logging_supported":true}},"ata_sct_capabilities":{"value":61,"error_recovery_control_supported":true,"feature_control_supported":true,"data_table_supported":true},"ata_smart_attributes":{"revision":1,"table":[{"id":5,"name":"Reallocated_Sector_Ct","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":51,"string":"PO--CK ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":9,"name":"Power_On_Hours","value":97,"worst":97,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":11464,"string":"11464"}},{"id":12,"name":"Power_Cycle_Count","value":99,"worst":99,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":47,"string":"47"}},{"id":177,"name":"Wear_Leveling_Count","value":99,"worst":99,"thresh":5,"when_failed":"","flags":{"value":19,"string":"PO--C- ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":false},"raw":{"value":27,"string":"27"}},{"id":179,"name":"Used_Rsvd_Blk_Cnt_Tot","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":19,"string":"PO--C- ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":false},"raw":{"value":0,"string":"0"}},{"id":180,"name":"Unused_Rsvd_Blk_Cnt_Tot","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":19,"string":"PO--C- ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":false},"raw":{"value":1728,"string":"1728"}},{"id":181,"name":"Program_Fail_Cnt_Total","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":182,"name":"Erase_Fail_Count_Total","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":183,"name":"Runtime_Bad_Block","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":19,"string":"PO--C- ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":false},"raw":{"value":0,"string":"0"}},{"id":184,"name":"End-to-End_Error","value":100,"worst":100,"thresh":97,"when_failed":"","flags":{"value":51,"string":"PO--CK ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":187,"name":"Reported_Uncorrect","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":190,"name":"Airflow_Temperature_Cel","value":73,"worst":54,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":27,"string":"27"}},{"id":194,"name":"Temperature_Celsius","value":73,"worst":45,"thresh":0,"when_failed":"","flags":{"value":34,"string":"-O---K ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":false,"auto_keep":true},"raw":{"value":197570134043,"string":"27 (Min/Max 25/46)"}},{"id":195,"name":"Hardware_ECC_Recovered","value":200,"worst":200,"thresh":0,"when_failed":"","flags":{"value":26,"string":"-O-RC- ","prefailure":false,"updated_online":true,"performance":false,"error_rate":true,"event_count":true,"auto_keep":false},"raw":{"value":0,"string":"0"}},{"id":197,"name":"Current_Pending_Sector","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":199,"name":"UDMA_CRC_Error_Count","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":62,"string":"-OSRCK ","prefailure":false,"updated_online":true,"performance":true,"error_rate":true,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":202,"name":"Unknown_SSD_Attribute","value":100,"worst":100,"thresh":10,"when_failed":"","flags":{"value":51,"string":"PO--CK ","prefailure":true,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":235,"name":"Unknown_Attribute","value":99,"worst":99,"thresh":0,"when_failed":"","flags":{"value":18,"string":"-O--C- ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":false},"raw":{"value":35,"string":"35"}},{"id":241,"name":"Total_LBAs_Written","value":99,"worst":99,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":30471720553,"string":"30471720553"}},{"id":242,"name":"Total_LBAs_Read","value":99,"worst":99,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":114305652735,"string":"114305652735"}},{"id":243,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":244,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}},{"id":245,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":65535,"string":"65535"}},{"id":246,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":65535,"string":"65535"}},{"id":247,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":65535,"string":"65535"}},{"id":251,"name":"Unknown_Attribute","value":100,"worst":100,"thresh":0,"when_failed":"","flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":33611104576,"string":"33611104576"}}]},"power_on_time":{"hours":11464},"power_cycle_count":47,"temperature":{"current":27},"ata_smart_error_log":{"summary":{"revision":1,"count":0}},"ata_smart_self_test_log":{"standard":{"revision":1,"table":[{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3022},{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3021},{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3020},{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3020},{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3019},{"type":{"value":1,"string":"Short offline"},"status":{"value":0,"string":"Completed without error","passed":true},"lifetime_hours":3019}],"count":6,"error_count_total":0,"error_count_outdated":0}},"ata_smart_selective_self_test_log":{"revision":1,"table":[{"lba_min":0,"lba_max":0,"status":{"value":0,"string":"Not_testing"}},{"lba_min":0,"lba_max":0,"status":{"value":0,"string":"Not_testing"}},{"lba_min":0,"lba_max":0,"status":{"value":0,"string":"Not_testing"}},{"lba_min":0,"lba_max":0,"status":{"value":0,"string":"Not_testing"}},{"lba_min":0,"lba_max":0,"status":{"value":0,"string":"Not_testing"}}],"current_read_scan":{"lba_min":0,"lba_max":65535,"status":{"value":0,"string":"was never started"}},"flags":{"value":0,"remainder_scan_enabled":false},"power_up_scan_resume_minutes":0}}"""
    ],
]

SECTION_SMART_POSIX_SCAN_ARG = Section(
    devices={
        "SAMSUNG MZ7L31T9HBLT-00A07 S6ESNC0W622008": ATAAll(
            device=ATADevice(protocol="ATA", name="/dev/bus/0"),
            model_name="SAMSUNG MZ7L31T9HBLT-00A07",
            serial_number="S6ESNC0W622008",
            ata_smart_attributes=ATATable(
                table=[
                    ATATableEntry(
                        id=5,
                        name="Reallocated_Sector_Ct",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=9,
                        name="Power_On_Hours",
                        value=97,
                        thresh=0,
                        raw=ATARawValue(value=11464),
                    ),
                    ATATableEntry(
                        id=12,
                        name="Power_Cycle_Count",
                        value=99,
                        thresh=0,
                        raw=ATARawValue(value=47),
                    ),
                    ATATableEntry(
                        id=177,
                        name="Wear_Leveling_Count",
                        value=99,
                        thresh=5,
                        raw=ATARawValue(value=27),
                    ),
                    ATATableEntry(
                        id=179,
                        name="Used_Rsvd_Blk_Cnt_Tot",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=180,
                        name="Unused_Rsvd_Blk_Cnt_Tot",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=1728),
                    ),
                    ATATableEntry(
                        id=181,
                        name="Program_Fail_Cnt_Total",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=182,
                        name="Erase_Fail_Count_Total",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=183,
                        name="Runtime_Bad_Block",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=184,
                        name="End-to-End_Error",
                        value=100,
                        thresh=97,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=187,
                        name="Reported_Uncorrect",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=190,
                        name="Airflow_Temperature_Cel",
                        value=73,
                        thresh=0,
                        raw=ATARawValue(value=27),
                    ),
                    ATATableEntry(
                        id=194,
                        name="Temperature_Celsius",
                        value=73,
                        thresh=0,
                        raw=ATARawValue(value=197570134043),
                    ),
                    ATATableEntry(
                        id=195,
                        name="Hardware_ECC_Recovered",
                        value=200,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=197,
                        name="Current_Pending_Sector",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=199,
                        name="UDMA_CRC_Error_Count",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=202,
                        name="Unknown_SSD_Attribute",
                        value=100,
                        thresh=10,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=235,
                        name="Unknown_Attribute",
                        value=99,
                        thresh=0,
                        raw=ATARawValue(value=35),
                    ),
                    ATATableEntry(
                        id=241,
                        name="Total_LBAs_Written",
                        value=99,
                        thresh=0,
                        raw=ATARawValue(value=30471720553),
                    ),
                    ATATableEntry(
                        id=242,
                        name="Total_LBAs_Read",
                        value=99,
                        thresh=0,
                        raw=ATARawValue(value=114305652735),
                    ),
                    ATATableEntry(
                        id=243,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=244,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=0),
                    ),
                    ATATableEntry(
                        id=245,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=65535),
                    ),
                    ATATableEntry(
                        id=246,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=65535),
                    ),
                    ATATableEntry(
                        id=247,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=65535),
                    ),
                    ATATableEntry(
                        id=251,
                        name="Unknown_Attribute",
                        value=100,
                        thresh=0,
                        raw=ATARawValue(value=33611104576),
                    ),
                ]
            ),
            temperature=Temperature(current=27),
        ),
        "DELL PERC H740P Mini 0098f53cb2b061dd2c00f4f469f0a7ce": SCSIAll(
            device=SCSIDevice(protocol="SCSI", name="/dev/sda"),
            model_name="DELL PERC H740P Mini",
            serial_number="0098f53cb2b061dd2c00f4f469f0a7ce",
            temperature=Temperature(current=0),
            scsi_temperature=SCSITemperature(drive_trip=0),
        ),
    },
    failures=[
        CantOpenDevice(
            device=SCSIDevice(protocol="SCSI", name="/dev/sdb"),
            smartctl=SmartctlError(exit_status=4),
        )
    ],
)


def test_parse_smart_posix_scan_arg() -> None:
    assert parse_smart_posix(SMART_POSIX_SCAN_ARG) == SECTION_SMART_POSIX_SCAN_ARG


def test_discover_temperature_scsi() -> None:
    services = list(
        discovery_smart_scsi_temp(SECTION_SMART_POSIX_ALL, SECTION_SMART_POSIX_SCAN_ARG)
    )
    assert services == []
