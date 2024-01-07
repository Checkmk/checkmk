#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.temperature import (
    aggregate_temperature_results,
    check_temperature,
    TemperatureSensor,
    TempParamDict,
)

from .health import check_hp_msa_health, discover_hp_msa_health
from .lib import parse_hp_msa, Section

# drives 1 durable-id disk_01.01
# drives 1 enclosure-id 1
# drives 1 drawer-id 255
# drives 1 slot 1
# drives 1 location 1.1
# drives 1 port 0
# drives 1 scsi-id 0
# drives 1 blocks 1172123568
# drives 1 serial-number W7GB13NV
# drives 1 vendor HP
# drives 1 model EG0600FBVFP
# drives 1 revision HPDC
# drives 1 secondary-channel 0
# drives 1 container-index 0
# drives 1 member-index 0
# drives 1 description SAS
# drives 1 description-numeric 4
# drives 1 architecture HDD
# drives 1 architecture-numeric 1
# drives 1 interface SAS
# drives 1 interface-numeric 0
# drives 1 single-ported Disabled
# drives 1 single-ported-numeric 0
# drives 1 type SAS
# drives 1 type-numeric 4
# drives 1 usage LINEAR POOL
# drives 1 usage-numeric 1
# drives 1 job-running
# drives 1 job-running-numeric 0
# drives 1 state LINEAR POOL
# drives 1 current-job-completion
# drives 1 blink 0
# drives 1 locator-led Off
# drives 1 locator-led-numeric 0
# drives 1 speed 0
# drives 1 smart Enabled
# drives 1 smart-numeric 1
# drives 1 dual-port 1
# drives 1 error 0
# drives 1 fc-p1-channel 0
# drives 1 fc-p1-device-id 0
# drives 1 fc-p1-node-wwn 5000CCA07014111C
# drives 1 fc-p1-port-wwn 0000000000000000
# drives 1 fc-p1-unit-number 0
# drives 1 fc-p2-channel 0
# drives 1 fc-p2-device-id 0
# drives 1 fc-p2-node-wwn
# drives 1 fc-p2-port-wwn
# drives 1 fc-p2-unit-number 0
# drives 1 drive-down-code 0
# drives 1 owner A
# drives 1 owner-numeric 1
# drives 1 index 0
# drives 1 rpm 10
# drives 1 size 600.1GB
# drives 1 size-numeric 1172123568
# drives 1 sector-format 512n
# drives 1 sector-format-numeric 0
# drives 1 transfer-rate 6.0
# drives 1 transfer-rate-numeric 3
# drives 1 attributes
# drives 1 attributes-numeric 2
# drives 1 enclosure-wwn 500C0FF01E82BB3C
# drives 1 recon-state N/A
# drives 1 recon-state-numeric 0
# drives 1 copyback-state N/A
# drives 1 copyback-state-numeric 0
# drives 1 virtual-disk-serial 00c0ff1ec44a00001e23415500000000
# drives 1 disk-group IMSAKO2B1_U1_B01-04
# drives 1 storage-pool-name IMSAKO2B1_U1_B01-04
# drives 1 storage-tier N/A
# drives 1 storage-tier-numeric 0
# drives 1 ssd-life-left N/A
# drives 1 ssd-life-left-numeric 255
# drives 1 led-status-numeric 1
# drives 1 disk-dsd-count 0
# drives 1 spun-down 0
# drives 1 number-of-ios 0
# drives 1 total-data-transferred 0B
# drives 1 total-data-transferred-numeric 0
# drives 1 avg-rsp-time 0
# drives 1 fde-state Not FDE Capable
# drives 1 fde-state-numeric 1
# drives 1 lock-key-id 00000000
# drives 1 import-lock-key-id 00000000
# drives 1 fde-config-time N/A
# drives 1 fde-config-time-numeric 0
# drives 1 pi-formatted Unsupported
# drives 1 pi-formatted-numeric 4
# drives 1 power-on-hours 2663
# drives 1 health OK
# drives 1 health-numeric 0
# drives 1 health-reason
# drives 1 health-recommendation
# disk-statistics 1 durable-id disk_01.01
# disk-statistics 1 serial-number W7GB13NV
# disk-statistics 1 bytes-per-second 771.0KB
# disk-statistics 1 bytes-per-second-numeric 771072
# disk-statistics 1 iops 13
# disk-statistics 1 number-of-reads 49797666
# disk-statistics 1 number-of-writes 20095262
# disk-statistics 1 data-read 50.6TB
# disk-statistics 1 data-read-numeric 50656968970752
# disk-statistics 1 data-written 2800.2GB
# disk-statistics 1 data-written-numeric 2800282933760
# disk-statistics 1 queue-depth 0
# disk-statistics 1 reset-time 2015-05-22 13:55:39
# disk-statistics 1 reset-time-numeric 1432302939
# disk-statistics 1 start-sample-time 2015-08-18 10:37:02
# disk-statistics 1 start-sample-time-numeric 1439894222
# disk-statistics 1 stop-sample-time 2015-08-18 11:09:27
# disk-statistics 1 stop-sample-time-numeric 1439896167
# disk-statistics 1 smart-count-1 0
# disk-statistics 1 io-timeout-count-1 0
# disk-statistics 1 no-response-count-1 0
# disk-statistics 1 spinup-retry-count-1 0
# disk-statistics 1 number-of-media-errors-1 0
# disk-statistics 1 number-of-nonmedia-errors-1 6
# disk-statistics 1 number-of-block-reassigns-1 0
# disk-statistics 1 number-of-bad-blocks-1 0
# disk-statistics 1 smart-count-2 0
# disk-statistics 1 io-timeout-count-2 0
# disk-statistics 1 no-response-count-2 0
# disk-statistics 1 spinup-retry-count-2 0
# disk-statistics 1 number-of-media-errors-2 0
# disk-statistics 1 number-of-nonmedia-errors-2 1
# disk-statistics 1 number-of-block-reassigns-2 0
# disk-statistics 1 number-of-bad-blocks-2 0


agent_section_hp_msa_disk = AgentSection(
    name="hp_msa_disk",
    parse_function=parse_hp_msa,
)

check_plugin_hp_msa_disk = CheckPlugin(
    name="hp_msa_disk",
    service_name="Disk Health %s",
    discovery_function=discover_hp_msa_health,
    check_function=check_hp_msa_health,
)


def discovery_hp_msa_disk_temp(section: Section) -> DiscoveryResult:
    yield Service(item="Disks")


def check_hp_msa_disk_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    temp_and_ids = ((k, float(v["temperature-numeric"])) for k, v in section.items())
    yield from aggregate_temperature_results(
        [
            TemperatureSensor(
                k,
                temp,
                check_temperature(temp, params).reading,
            )
            for k, temp in temp_and_ids
        ],
        params,
        get_value_store(),
    )


check_plugin_hp_msa_disk_temp = CheckPlugin(
    name="hp_msa_disk_temp",
    service_name="Temperature %s",
    sections=["hp_msa_disk"],
    discovery_function=discovery_hp_msa_disk_temp,
    check_function=check_hp_msa_disk_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 45.0),  # just an assumption
    },
)

# .
