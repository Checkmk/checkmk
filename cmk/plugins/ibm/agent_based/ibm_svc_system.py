#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<ibm_svc_system:sep(58)>>>
# id:0000020060C16104
# name:BLUBB_NAME
# location:local
# partnership:
# bandwidth:
# total_mdisk_capacity:192.9TB
# space_in_mdisk_grps:192.9TB
# space_allocated_to_vdisks:147.48TB
# total_free_space:45.5TB
# total_vdiskcopy_capacity:149.54TB
# total_used_capacity:147.44TB
# total_overallocation:77
# total_vdisk_capacity:74.77TB
# total_allocated_extent_capacity:147.49TB
# statistics_status:on
# statistics_frequency:5
# cluster_locale:en_US
# time_zone:384 Europe/Paris
# code_level:6.4.1.4 (build 75.3.1303080000)
# console_IP:x.x.x.x:443
# id_alias:0000020060C16104
# gm_link_tolerance:300
# gm_inter_cluster_delay_simulation:0
# gm_intra_cluster_delay_simulation:0
# gm_max_host_delay:5
# email_reply:master@desaster
# email_contact:Wichtiger Admin
# email_contact_primary:+49 30 555555555
# email_contact_alternate:
# email_contact_location:blubb
# email_contact2:
# email_contact2_primary:
# email_contact2_alternate:
# email_state:running
# inventory_mail_interval:7
# cluster_ntp_IP_address:x.x.x.x
# cluster_isns_IP_address:
# iscsi_auth_method:none
# iscsi_chap_secret:
# auth_service_configured:no
# auth_service_enabled:no
# auth_service_url:
# auth_service_user_name:
# auth_service_pwd_set:no
# auth_service_cert_set:no
# auth_service_type:tip
# relationship_bandwidth_limit:25
# tier:generic_ssd
# tier_capacity:0.00MB
# tier_free_capacity:0.00MB
# tier:generic_hdd
# tier_capacity:192.94TB
# tier_free_capacity:45.46TB
# has_nas_key:no
# layer:replication
# rc_buffer_size:48
# compression_active:no
# compression_virtual_capacity:0.00MB
# compression_compressed_capacity:0.00MB
# compression_uncompressed_capacity:0.00MB
# cache_prefetch:on
# email_organization:Acme Inc
# email_machine_address:
# email_machine_city:Berlin
# email_machine_state:XX
# email_machine_zip:
# email_machine_country:DE
# total_drive_raw_capacity:0


from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True)
class System:
    name: str | None
    location: str | None
    code_level: str | None
    email_contact_location: str | None


def discover_ibm_svc_system(section: System) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_ibm_svc_system(section: System) -> CheckResult:
    parts = [
        f"{label}: {value}"
        for label, value in (
            ("name", section.name),
            ("location", section.location),
            ("code_level", section.code_level),
            ("email_contact_location", section.email_contact_location),
        )
        if value is not None
    ]
    yield Result(state=State.OK, summary=", ".join(parts))


def parse_ibm_svc_system(string_table: StringTable) -> System:
    values = {line[0]: line[1] for line in string_table if len(line) >= 2}
    return System(
        name=values.get("name"),
        location=values.get("location"),
        code_level=values.get("code_level"),
        email_contact_location=values.get("email_contact_location"),
    )


agent_section_ibm_svc_system = AgentSection(
    name="ibm_svc_system",
    parse_function=parse_ibm_svc_system,
)


check_plugin_ibm_svc_system = CheckPlugin(
    name="ibm_svc_system",
    service_name="Info",
    discovery_function=discover_ibm_svc_system,
    check_function=check_ibm_svc_system,
)
