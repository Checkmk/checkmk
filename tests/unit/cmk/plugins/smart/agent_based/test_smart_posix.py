#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.smart.agent_based.smart_posix import parse_smart_posix


def test_parse_sd_card_reader() -> None:
    """SD card reader from a Macbook Pro 13 (no card inserted in reader)"""
    string_table = [
        [
            """{"json_format_version":[1,0],"smartctl":{"version":[7,4],"pre_release":false,"svn_revision":"5530","platform_info":"x86_64-linux-6.12.7-arch1-1","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdb"],"exit_status":2},"local_time":{"time_t":1744724532,"asctime":"Tue Apr 15 15:42:12 2025 CEST"},"device":{"name":"/dev/sdb","info_name":"/dev/sdb [SAT]","type":"sat","protocol":"ATA"}}"""
        ]
    ]
    parse_smart_posix(string_table)


def test_parse_freebsd_ata_cam_layer() -> None:
    """Unknown device from support ticket

    atacam is  refers Common Access Method SCSI/ATA subsystem from FreeBSD. `/dev/ses1` is
    likely an SCSI device, but unclear.
    """
    string_table = [
        [
            """{"json_format_version":[1,0],"smartctl":{"version":[7,2],"svn_revision":"5236","platform_info":"FreeBSD 13.1-RELEASE-p9 amd64","build_info":"(local build)","argv":["smartctl","--all","--json","/dev/ses1"],"exit_status":2},"device":{"name":"/dev/ses1","info_name":"/dev/ses1","type":"atacam","protocol":"ATA"}}"""
        ]
    ]
    parse_smart_posix(string_table)


def test_parse_ata_identify_device_structure_missing_information() -> None:
    """Exit code 4, no model_name

    Exit code 4 means that ATA identify device structure missing information. This dump is from
    CMK-22090.
    """

    string_table = [
        [
            """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdb","-d","scsi"],"exit_status":4},"local_time":{"time_t":1740485276,"asctime":"Tue Feb 25 12:07:56 2025 GMT"},"device":{"name":"/dev/sdb","info_name":"/dev/sdb","type":"scsi","protocol":"SCSI"},"user_capacity":{"blocks":468731008,"bytes":239990276096},"logical_block_size":512,"physical_block_size":4096,"scsi_lb_provisioning":{"name":"not reported","value":0,"management_enabled":{"name":"LBPME","value":1},"read_zeros":{"name":"LBPRZ","value":0}},"rotation_rate":0,"serial_number":"dd8b62ae0b480010","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":false},"temperature":{"current":0},"scsi_temperature":{"drive_trip":0}}"""
        ]
    ]
    parse_smart_posix(string_table)


def test_parse_unable_to_detect_device() -> None:
    string_table = [
        [
            """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda"],"messages":[{"string":"Smartctl open device: /dev/sda failed: DELL or MegaRaid controller, please try adding '-d megaraid,N'","severity":"error"}],"exit_status":2},"local_time":{"time_t":1740483986,"asctime":"Tue Feb 25 11:46:26 2025 GMT"}}"""
        ]
    ]
    parse_smart_posix(string_table)


@pytest.mark.xfail(strict=True)
def test_parse_missing_tresh_ata_attributes() -> None:
    string_table = [
        [  # Edited serial number, removed ata_smart_data, interface_speed, and most ata_smart_attributes in table
            """{"json_format_version":[1,0],"smartctl":{"version":[7,4],"pre_release":false,"svn_revision":"5530","platform_info":"x86_64-linux-6.8.0-71-generic","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdc"],"drive_database_version":{"string":"7.3/5816"},"exit_status":0},"local_time":{"time_t":1755670096,"asctime":"Wed Aug 20 08:08:16 2025 CEST"},"device":{"name":"/dev/sdc","info_name":"/dev/sdc [SAT]","type":"sat","protocol":"ATA"},"model_family":"Marvell based SanDisk SSDs","model_name":"SanDisk SDSSDHP256G","serial_number":"XXX","wwn":{"naa":5,"oui":6980,"id":45002415621},"firmware_version":"X2306RL","user_capacity":{"blocks":500118192,"bytes":256060514304},"logical_block_size":512,"physical_block_size":512,"rotation_rate":0,"form_factor":{"ata_value":10},"trim":{"supported":true,"deterministic":true,"zeroed":true},"in_smartctl_database":true,"ata_version":{"string":"ATA8-ACS T13/1699-D revision 6","major_value":496,"minor_value":40},"sata_version":{"string":"SATA 3.0","value":63},"interface_speed":{"max":{"sata_value":14,"string":"6.0 Gb/s","units_per_second":60,"bits_per_unit":100000000},"current":{"sata_value":3,"string":"6.0 Gb/s","units_per_second":60,"bits_per_unit":100000000}},"smart_support":{"available":true,"enabled":true},"smart_status":{"passed":true},"ata_smart_data":{"offline_data_collection":{"status":{"value":0,"string":"was never started"},"completion_seconds":0},"self_test":{"status":{"value":0,"string":"completed without error","passed":true},"polling_minutes":{"short":2,"extended":10}},"capabilities":{"values":[17,3],"exec_offline_immediate_supported":true,"offline_is_aborted_upon_new_cmd":false,"offline_surface_scan_supported":false,"self_tests_supported":true,"conveyance_self_test_supported":false,"selective_self_test_supported":false,"attribute_autosave_enabled":true,"error_logging_supported":true,"gp_logging_supported":true}},"ata_smart_attributes":{"revision":4,"table":[{"id":243,"name":"Unknown_Marvell_Attr","value":100,"worst":100,"flags":{"value":50,"string":"-O--CK ","prefailure":false,"updated_online":true,"performance":false,"error_rate":false,"event_count":true,"auto_keep":true},"raw":{"value":0,"string":"0"}}]},"power_on_time":{"hours":172},"power_cycle_count":61,"temperature":{"current":24},"ata_smart_error_log":{"summary":{"revision":1,"count":0}},"ata_smart_self_test_log":{"standard":{"revision":1,"count":0}}}"""
        ]
    ]
    parse_smart_posix(string_table)
