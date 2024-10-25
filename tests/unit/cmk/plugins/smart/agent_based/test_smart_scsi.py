#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.smart.agent_based.smart_posix import (
    parse_smart_posix_all,
    SCSIAll,
    SCSIDevice,
    Temperature,
)

STRING_TABLE_SCSI = [  # unmodified except for serial number
    [
        '{ "json_format_version": [ 1, 0 ], "smartctl": { "version": [ 7, 2 ], "svn_revision": "5236", "platform_info": "FreeBSD 13.1-RELEASE-p9 amd64", "build_info": "(local build)", "argv": [ "smartctl", "--all", "--json", "/dev/da5" ], "exit_status": 0 }, "device": { "name": "/dev/da5", "info_name": "/dev/da5", "type": "scsi", "protocol": "SCSI" }, "vendor": "TOSHIBA", "product": "AL13SXB60EN", "model_name": "TOSHIBA AL13SXB60EN", "revision": "5702", "scsi_version": "SPC-4", "user_capacity": { "blocks": 1172123568, "bytes": 600127266816 }, "logical_block_size": 512, "rotation_rate": 15000, "form_factor": { "scsi_value": 3, "name": "2.5 inches" }, "serial_number": "XXX", "device_type": { "scsi_value": 0, "name": "disk" }, "local_time": { "time_t": 1728902031, "asctime": "Mon Oct 14 10:33:51 2024 UTC" }, "smart_status": { "passed": true }, "temperature": { "current": 41, "drive_trip": 65 }, "power_on_time": { "hours": 64579, "minutes": 53 }, "scsi_grown_defect_list": 0, "scsi_error_counter_log": { "read": { "errors_corrected_by_eccfast": 0, "errors_corrected_by_eccdelayed": 2657, "errors_corrected_by_rereads_rewrites": 0, "total_errors_corrected": 0, "correction_algorithm_invocations": 0, "gigabytes_processed": "3237519.423", "total_uncorrected_errors": 0 }, "write": { "errors_corrected_by_eccfast": 0, "errors_corrected_by_eccdelayed": 0, "errors_corrected_by_rereads_rewrites": 0, "total_errors_corrected": 0, "correction_algorithm_invocations": 0, "gigabytes_processed": "1086347.509", "total_uncorrected_errors": 0 } } }'
    ]
]


def test_parse_smart_scsi() -> None:
    section = parse_smart_posix_all(STRING_TABLE_SCSI)
    assert section == [
        SCSIAll(
            device=SCSIDevice(protocol="SCSI", name="/dev/da5"), temperature=Temperature(current=41)
        )
    ]
