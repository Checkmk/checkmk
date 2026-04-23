#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.base.config import ConfigCache
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.core.interface import MonitoringCore
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.core_client import NagiosClient
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.snmplib import SNMPPluginStore
from cmk.utils import paths
from cmk.utils.labels import LabelManager
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.timeperiod import get_all_timeperiods


def create_core(
    edition: Edition,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
    loaded_config: LoadedConfigFragment,
    snmp_plugin_store: SNMPPluginStore,
    config_cache: ConfigCache,
    plugins: AgentBasedPlugins,
) -> MonitoringCore:
    match loaded_config.monitoring_core:
        case "nagios":
            from cmk.base.core.nagios import NagiosCore
            from cmk.base.core.nagios._create_config import NagiosCoreConfig

            return NagiosCore(
                NagiosClient(
                    objects_file=paths.nagios_objects_file,
                    init_script=paths.nagios_startscript,
                    config_file=paths.nagios_config_file,
                    binary_file=paths.nagios_binary,
                    cleanup_base=paths.omd_root,
                ),
                CommunityLicensingHandler,
                get_all_timeperiods(loaded_config.timeperiods),
                NagiosCoreConfig(
                    delay_precompile=loaded_config.delay_precompile,
                    host_template=loaded_config.host_template,
                    cluster_template=loaded_config.cluster_template,
                    pingonly_template=loaded_config.pingonly_template,
                    active_service_template=loaded_config.active_service_template,
                    passive_service_template_perf=loaded_config.passive_service_template_perf,
                    inventory_check_template=loaded_config.inventory_check_template,
                    service_dependency_template=loaded_config.service_dependency_template,
                    generate_hostconf=loaded_config.generate_hostconf,
                    generate_dummy_commands=loaded_config.generate_dummy_commands,
                    dummy_check_commandline=loaded_config.dummy_check_commandline,
                    default_host_group=loaded_config.default_host_group,
                    extra_nagios_conf=loaded_config.extra_nagios_conf,
                    contacts=loaded_config.contacts,
                    define_contactgroups=loaded_config.define_contactgroups,
                    define_hostgroups=loaded_config.define_hostgroups,
                    define_servicegroups=loaded_config.define_servicegroups,
                    contactgroup_members=loaded_config.contactgroup_members,
                ),
            )
        case "cmc":
            raise RuntimeError("The Microcore is not available in this edition")
        case other_core:
            assert_never(other_core)
