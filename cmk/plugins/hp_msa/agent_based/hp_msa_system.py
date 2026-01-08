#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"


from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, CheckPlugin, StringTable

from .health import check_hp_msa_health, discover_hp_msa_health

# <<<hp_msa_system>>>
# system 1 system-name IMSAKO2B1
# system 1 system-contact cia@cgm.com
# system 1 system-location Rack B1
# system 1 system-information Uninitialized Info
# system 1 midplane-serial-number 00C0FF1E82BB
# system 1 vendor-name HP
# system 1 product-id MSA 2040 SAN
# system 1 product-brand MSA Storage
# system 1 scsi-vendor-id HP
# system 1 scsi-product-id MSA 2040 SAN
# system 1 enclosure-count 1
# system 1 health OK
# system 1 health-numeric 0
# system 1 health-reason
# system 1 other-MC-status Operational
# system 1 other-MC-status-numeric 4754
# system 1 pfuStatus Idle
# system 1 supported-locales English (English), Spanish (español), French (français), German (Deutsch), Italian (italiano), Japanese (日本語), Dutch (Nederlands), Chinese-Simplified (简体中文), Chinese-Traditional (繁體中文), Korean (한국어)
# system 1 current-node-wwn 208000c0ff1e82bb
# system 1 fde-security-status Unsecured
# system 1 fde-security-status-numeric 1
# system 1 platform-type Gallium
# system 1 platform-type-numeric 3
# system 1 platform-brand HP Cardinals
# system 1 platform-brand-numeric 15
# redundancy 2 redundancy-mode Active-Active ULP
# redundancy 2 redundancy-mode-numeric 8
# redundancy 2 redundancy-status Redundant
# redundancy 2 redundancy-status-numeric 2
# redundancy 2 controller-a-status Operational
# redundancy 2 controller-a-status-numeric 0
# redundancy 2 controller-a-serial-number 7CE501N158
# redundancy 2 controller-b-status Operational
# redundancy 2 controller-b-status-numeric 0
# redundancy 2 controller-b-serial-number 7CE501M190
# redundancy 2 other-MC-status Operational
# redundancy 2 other-MC-status-numeric 4754


def parse_hp_msa_system(string_table: StringTable) -> Mapping[str, Mapping[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for line in string_table:
        if line[2] == "system-name":
            system_name = " ".join(line[3:])
            parsed[system_name] = {"item_type": line[0]}
        elif line[2] == "health-numeric":
            parsed[system_name]["health-numeric"] = line[3]
        elif line[2] == "health-reason":
            parsed[system_name]["health-reason"] = " ".join(line[3:])

    return parsed


agent_section_hp_msa_system = AgentSection(
    name="hp_msa_system",
    parse_function=parse_hp_msa_system,
)

check_plugin_hp_msa_system = CheckPlugin(
    name="hp_msa_system",
    service_name="System Health %s",
    discovery_function=discover_hp_msa_health,
    check_function=check_hp_msa_health,
)
