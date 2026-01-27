#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.utils.labels import ABCLabelConfig, LabelManager, Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

EMPTY_CONFIG = LoadedConfigFragment(
    experimental={},
    discovery_rules={},
    checkgroup_parameters={},
    static_checks={},
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
    fallback_agent_output_encoding="latin-1",
    folder_attributes={},
    agent_config={},
    agent_port=6556,
    agent_ports=(),
    tcp_connect_timeout=5.0,
    tcp_connect_timeouts=(),
    encryption_handling=(),
    piggyback_translation=(),
    piggybacked_host_files=(),
    piggyback_max_cachefile_age=3600,
    agent_encryption=(),
    agent_exclude_sections=(),
    cmc_real_time_checks=None,
    snmp_check_interval=[],
    agent_bakery_logging=None,
    apply_bake_revision=False,
    bake_agents_on_restart=False,
    is_distributed_setup_remote_site=False,
    simulation_mode=False,
    use_dns_cache=True,
    ipaddresses={},
    ipv6addresses={},
    inventory_check_interval=None,
    fake_dns=None,
    tag_config={
        "tag_groups": [],
        "aux_tags": [],
    },
    host_tags={},
    cmc_log_rrdcreation=None,
    cmc_host_rrd_config=[],
    cmc_statehist_cache={"horizon": 63072000, "max_core_downtime": 30},
    cmc_timeperiod_horizon=2 * 365,
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
    cmc_log_levels={
        "cmk.alert": 5,
        "cmk.carbon": 5,
        "cmk.core": 5,
        "cmk.downtime": 5,
        "cmk.helper": 5,
        "cmk.livestatus": 5,
        "cmk.notification": 5,
        "cmk.rrd": 5,
        "cmk.influxdb": 5,
        "cmk.smartping": 5,
    },
    cluster_max_cachefile_age=90,
    http_proxies={},
    oauth2_connections={},
    extra_service_conf={},
    timeperiods={},
    check_periods=(),
    relays={},
    cmc_config_multiprocessing={"use_multiprocessing": True},
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
