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
from cmk.plugins.smart.agent_based.smart_nvme import check_smart_nvme, discover_smart_nvme
from cmk.plugins.smart.agent_based.smart_posix import (
    NVMeAll,
    NVMeDevice,
    NVMeHealth,
    parse_smart_posix_all,
)

STRING_TABLE_NVME = [
    [  # unmodified except serial number
        '{"json_format_version":[1,0],"smartctl":{"version":[7,2],"svn_revision":"5155","platform_info":"x86_64-linux-6.8.0-45-generic","build_info":"(local build)","argv":["smartctl","--all","--json=c","/dev/nvme0"],"exit_status":0},"device":{"name":"/dev/nvme0","info_name":"/dev/nvme0","type":"nvme","protocol":"NVMe"},"model_name":"PC601 NVMe SK hynix 512GB","serial_number":"XXXNVMe","firmware_version":"80002111","nvme_pci_vendor":{"id":7260,"subsystem_id":7260},"nvme_ieee_oui_identifier":11330606,"nvme_controller_id":1,"nvme_version":{"string":"1.3","value":66304},"nvme_number_of_namespaces":1,"nvme_namespaces":[{"id":1,"size":{"blocks":1000215216,"bytes":512110190592},"capacity":{"blocks":1000215216,"bytes":512110190592},"utilization":{"blocks":1000215216,"bytes":512110190592},"formatted_lba_size":512,"eui64":{"oui":11330606,"ext_id":169815826}}],"user_capacity":{"blocks":1000215216,"bytes":512110190592},"logical_block_size":512,"local_time":{"time_t":1728742624,"asctime":"Sat Oct 12 16:17:04 2024 CEST"},"smart_status":{"passed":true,"nvme":{"value":0}},"nvme_smart_health_information_log":{"critical_warning":0,"temperature":44,"available_spare":100,"available_spare_threshold":50,"percentage_used":2,"data_units_read":46988993,"data_units_written":41549752,"host_reads":879699783,"host_writes":988581676,"controller_busy_time":2316,"power_cycles":2982,"power_on_hours":9944,"unsafe_shutdowns":676,"media_errors":0,"num_err_log_entries":0,"warning_temp_time":0,"critical_comp_time":0,"temperature_sensors":[44,43]},"temperature":{"current":44},"power_cycle_count":2982,"power_on_time":{"hours":9944}}'
    ],
]

SECTION_NVME = [
    NVMeAll(
        device=NVMeDevice(protocol="NVMe", name="/dev/nvme0"),
        nvme_smart_health_information_log=NVMeHealth(
            power_on_hours=9944,
            power_cycles=2982,
            critical_warning=0,
            media_errors=0,
            available_spare=100,
            available_spare_threshold=50,
            temperature=44,
            percentage_used=2,
            num_err_log_entries=0,
            data_units_read=46988993,
            data_units_written=41549752,
        ),
    )
]


def test_parse_smart_nvme() -> None:
    section = parse_smart_posix_all(STRING_TABLE_NVME)
    assert section == SECTION_NVME


def test_discover_smart_nvme_stat() -> None:
    assert list(discover_smart_nvme(SECTION_NVME)) == [
        Service(item="/dev/nvme0", parameters={"critical_warning": 0, "media_errors": 0}),
    ]


def test_check_smart_nvme_stat() -> None:
    assert list(
        check_smart_nvme("/dev/nvme0", {"critical_warning": 0, "media_errors": 0}, SECTION_NVME)
    ) == [
        Result(state=State.OK, summary="Powered on: 1 year 49 days"),
        Metric("uptime", 35798400.0),
        Result(state=State.OK, summary="Power cycles: 2982"),
        Metric("harddrive_power_cycles", 2982.0),
        Result(state=State.OK, summary="Critical warning: 0"),
        Metric("nvme_critical_warning", 0.0),
        Result(state=State.OK, summary="Media and data integrity errors: 0"),
        Metric("nvme_media_and_data_integrity_errors", 0.0),
        Result(state=State.OK, summary="Available spare: 100.00%"),
        Metric("nvme_available_spare", 100.0),
        Result(state=State.OK, summary="Percentage used: 2.00%"),
        Metric("nvme_spare_percentage_used", 2.0),
        Result(state=State.OK, summary="Error information log entries: 0"),
        Metric("nvme_error_information_log_entries", 0.0),
        Result(state=State.OK, summary="Data units read: 21.9 TiB"),
        Metric("nvme_data_units_read", 24058364416000.0),
        Result(state=State.OK, summary="Data units written: 19.3 TiB"),
        Metric("nvme_data_units_written", 21273473024000.0),
    ]
