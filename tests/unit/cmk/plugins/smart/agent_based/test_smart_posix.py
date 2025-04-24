#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
