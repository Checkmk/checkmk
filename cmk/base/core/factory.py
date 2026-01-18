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
from cmk.fetchers.snmp import SNMPPluginStore
from cmk.utils import paths
from cmk.utils.labels import LabelManager
from cmk.utils.licensing.community_handler import CRELicensingHandler
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

            return NagiosCore(
                NagiosClient(
                    objects_file=paths.nagios_objects_file,
                    init_script=paths.nagios_startscript,
                    cleanup_base=paths.omd_root,
                ),
                CRELicensingHandler,
                get_all_timeperiods(loaded_config.timeperiods),
            )
        case "cmc":
            raise RuntimeError("The Microcore is not available in this edition")
        case other_core:
            assert_never(other_core)
