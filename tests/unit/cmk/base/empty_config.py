#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.labels import ABCLabelConfig, LabelManager, Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from cmk.base.config import LoadedConfigFragment

EMPTY_CONFIG = LoadedConfigFragment(
    discovery_rules={},
    checkgroup_parameters={},
    service_rule_groups=set(),
    service_descriptions={},
    service_description_translation=(),
    use_new_descriptions_for=(),
    monitoring_core="nagios",
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
    cmc_log_rrdcreation=None,
    cmc_host_rrd_config=[],
    host_recurring_downtimes=[],
    cmc_flap_settings=(3.0, 5.0, 0.1),
    cmc_host_flap_settings=[],
    cmc_host_long_output_in_monitoring_history=[],
    host_state_translation=[],
    cmc_smartping_settings=[],
    cmc_service_rrd_config=[],
    service_recurring_downtimes=[],
    cmc_service_flap_settings=[],
    cmc_service_long_output_in_monitoring_history=[],
    service_state_translation=[],
    cmc_check_timeout=60,
    cmc_service_check_timeout=[],
    cmc_graphite_host_metrics=[],
    cmc_graphite_service_metrics=[],
    cmc_influxdb_service_metrics=[],
)


class EmptyLabelConfig(ABCLabelConfig):
    def host_labels(self, hn: object) -> Labels:
        return {}

    def service_labels(self, hn: object, sd: object, sn: object) -> Labels:
        return {}


def make_trivial_label_manager() -> LabelManager:
    return LabelManager(EmptyLabelConfig(), {}, {}, {})


def make_trivial_ruleset_matcher() -> RulesetMatcher:
    return RulesetMatcher({}, {}, frozenset(), {}, {})
