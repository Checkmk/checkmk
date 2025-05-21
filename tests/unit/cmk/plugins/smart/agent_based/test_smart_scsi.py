#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Service, ServiceLabel
from cmk.plugins.smart.agent_based.smart_posix import (
    parse_smart_posix,
    SCSIAll,
    SCSIDevice,
    SCSIMissingModel,
    SCSITemperature,
    Section,
    Temperature,
)
from cmk.plugins.smart.agent_based.smart_scsi import discovery_smart_scsi_temp

STRING_TABLE_SCSI = [  # unmodified except for serial number
    [
        '{ "json_format_version": [ 1, 0 ], "smartctl": { "version": [ 7, 2 ], "svn_revision": "5236", "platform_info": "FreeBSD 13.1-RELEASE-p9 amd64", "build_info": "(local build)", "argv": [ "smartctl", "--all", "--json", "/dev/da5" ], "exit_status": 0 }, "device": { "name": "/dev/da5", "info_name": "/dev/da5", "type": "scsi", "protocol": "SCSI" }, "vendor": "TOSHIBA", "product": "AL13SXB60EN", "model_name": "TOSHIBA AL13SXB60EN", "revision": "5702", "scsi_version": "SPC-4", "user_capacity": { "blocks": 1172123568, "bytes": 600127266816 }, "logical_block_size": 512, "rotation_rate": 15000, "form_factor": { "scsi_value": 3, "name": "2.5 inches" }, "serial_number": "XXX", "device_type": { "scsi_value": 0, "name": "disk" }, "local_time": { "time_t": 1728902031, "asctime": "Mon Oct 14 10:33:51 2024 UTC" }, "smart_status": { "passed": true }, "temperature": { "current": 41, "drive_trip": 65 }, "power_on_time": { "hours": 64579, "minutes": 53 }, "scsi_grown_defect_list": 0, "scsi_error_counter_log": { "read": { "errors_corrected_by_eccfast": 0, "errors_corrected_by_eccdelayed": 2657, "errors_corrected_by_rereads_rewrites": 0, "total_errors_corrected": 0, "correction_algorithm_invocations": 0, "gigabytes_processed": "3237519.423", "total_uncorrected_errors": 0 }, "write": { "errors_corrected_by_eccfast": 0, "errors_corrected_by_eccdelayed": 0, "errors_corrected_by_rereads_rewrites": 0, "total_errors_corrected": 0, "correction_algorithm_invocations": 0, "gigabytes_processed": "1086347.509", "total_uncorrected_errors": 0 } } }'
    ]
]


def test_parse_smart_scsi() -> None:
    section = parse_smart_posix(STRING_TABLE_SCSI)
    assert section == Section(
        devices={
            "TOSHIBA AL13SXB60EN XXX": SCSIAll(
                model_name="TOSHIBA AL13SXB60EN",
                serial_number="XXX",
                device=SCSIDevice(protocol="SCSI", name="/dev/da5"),
                temperature=Temperature(current=41, drive_trip=65),
            )
        },
        failures=[],
    )


def test_discover_temperature_scsi() -> None:
    section = parse_smart_posix(STRING_TABLE_SCSI)
    services = list(discovery_smart_scsi_temp(section, None))
    assert [
        Service(
            item="TOSHIBA AL13SXB60EN XXX",
            labels=[
                ServiceLabel("cmk/smart/type", "SCSI"),
                ServiceLabel("cmk/smart/device", "/dev/da5"),
                ServiceLabel("cmk/smart/model", "TOSHIBA AL13SXB60EN"),
                ServiceLabel("cmk/smart/serial", "XXX"),
            ],
        )
    ] == services


def test_parse_smart_scsi_7_3_regression() -> None:
    """model_name accidently replaced with scsi_model_name

    From the `smartmontools` change log:
        > scsiprint.cpp: Re-add JSON value 'model_name'.

        > This fixes a regression from r5286 (smartmontools 7.3).
        > Keep 'scsi_model_name' to provide backward compatibility with
        > release 7.3 and 7.4.
    """

    string_table_scsi = [  # unmodified except for serial number
        [
            """{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.8-4-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sda","-d","scsi"],"exit_status":4},"local_time":{"time_t":1740485276,"asctime":"Tue Feb 25 12:07:56 2025 GMT"},"device":{"name":"/dev/sda","info_name":"/dev/sda","type":"scsi","protocol":"SCSI"},"scsi_vendor":"DELL","scsi_product":"PERC H740P Mini","scsi_model_name":"DELL PERC H740P Mini","scsi_revision":"5.13","scsi_version":"SPC-3","user_capacity":{"blocks":22496673792,"bytes":11518296981504},"logical_block_size":512,"rotation_rate":0,"logical_unit_id":"0x62cea7f069f4f4002cdd61b0b23cf598","serial_number":"serialxxx","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":false},"temperature":{"current":0},"scsi_temperature":{"drive_trip":0}}"""
        ]
    ]
    section = parse_smart_posix(string_table_scsi)
    assert section == Section(
        devices={
            "DELL PERC H740P Mini serialxxx": SCSIAll(
                device=SCSIDevice(protocol="SCSI", name="/dev/sda"),
                model_name="DELL PERC H740P Mini",
                serial_number="serialxxx",
                temperature=Temperature(current=0),
                scsi_temperature=SCSITemperature(drive_trip=0),
            ),
        },
        failures=[],
    )


def test_parse_missing_model_name() -> None:
    """Samsung SSD 870 EVO 2TB does not yield a model name if passed `-d scsi`

    This happened on one of our internal servers, so we can gather more data if necessary. See
    `SCSIMissingModel` for details.
    """
    string_table = [
        [
            '{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.12-8-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdc","-d","scsi"],"exit_status":0},"local_time":{"time_t":1745560960,"asctime":"Fri Apr 25 08:02:40 2025 CEST"},"device":{"name":"/dev/sdc","info_name":"/dev/sdc","type":"scsi","protocol":"SCSI"},"user_capacity":{"blocks":3907029168,"bytes":2000398934016},"logical_block_size":512,"scsi_lb_provisioning":{"name":"fully provisioned","value":0,"management_enabled":{"name":"LBPME","value":-1},"read_zeros":{"name":"LBPRZ","value":0}},"rotation_rate":0,"form_factor":{"scsi_value":3,"name":"2.5 inches"},"logical_unit_id":"0x5002538f31b1fd8f","serial_number":"S6PPNJ0RB04XXX","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":true,"enabled":true},"temperature_warning":{"enabled":false},"smart_status":{"passed":true},"scsi_percentage_used_endurance_indicator":11,"temperature":{"current":21,"drive_trip":70},"power_on_time":{"hours":26195,"minutes":0}}'
        ],
        [
            '{"json_format_version":[1,0],"smartctl":{"version":[7,3],"svn_revision":"5338","platform_info":"x86_64-linux-6.8.12-8-pve","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/sdd","-d","scsi"],"exit_status":0},"local_time":{"time_t":1745560960,"asctime":"Fri Apr 25 08:02:40 2025 CEST"},"device":{"name":"/dev/sdd","info_name":"/dev/sdd","type":"scsi","protocol":"SCSI"},"user_capacity":{"blocks":3907029168,"bytes":2000398934016},"logical_block_size":512,"scsi_lb_provisioning":{"name":"fully provisioned","value":0,"management_enabled":{"name":"LBPME","value":-1},"read_zeros":{"name":"LBPRZ","value":0}},"rotation_rate":0,"form_factor":{"scsi_value":3,"name":"2.5 inches"},"logical_unit_id":"0x5002538f31b1fd8b","serial_number":"S6PPNJ0RB04XXX","device_type":{"scsi_terminology":"Peripheral Device Type [PDT]","scsi_value":0,"name":"disk"},"smart_support":{"available":true,"enabled":true},"temperature_warning":{"enabled":false},"smart_status":{"passed":true},"scsi_percentage_used_endurance_indicator":11,"temperature":{"current":22,"drive_trip":70},"power_on_time":{"hours":26195,"minutes":0}}'
        ],
    ]

    section = parse_smart_posix(string_table)
    assert sum(1 for scan in section.failures if isinstance(scan, SCSIMissingModel)) == len(
        string_table
    )
