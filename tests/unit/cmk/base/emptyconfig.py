#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import LoadedConfigFragment

EMPTYCONFIG = LoadedConfigFragment(
    discovery_rules={},
    checkgroup_parameters={},
    service_rule_groups=set(),
    service_descriptions={},
    service_description_translation=(),
    use_new_descriptions_for=(),
    nagios_illegal_chars="",
    cmc_illegal_chars="",
    all_hosts=(),
    clusters={},
    shadow_hosts={},
    service_dependencies=(),
    folder_attributes={},
    agent_config={},
    agent_ports=(),
    agent_encryption=(),
    agent_exclude_sections=(),
    cmc_real_time_checks=None,
    agent_bakery_logging=None,
    apply_bake_revision=False,
    bake_agents_on_restart=False,
    is_wato_slave_site=False,
    simulation_mode=False,
    use_dns_cache=True,
    ipaddresses={},
    ipv6addresses={},
    fake_dns=None,
    tag_config={
        "tag_groups": [],
        "aux_tags": [],
    },
    host_tags={},
)
