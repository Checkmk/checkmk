#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.base.config import ConfigCache
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.snmplib import SNMPPluginStore
from cmk.core_client import CoreClient, NagiosClient
from cmk.monitoring_config.internal import MonitoringConfigBuilder
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher
from cmk.utils import paths
from cmk.utils.timeperiod import get_all_timeperiods


def create_core(
    edition: Edition,  # noqa: ARG001
    matcher: RulesetMatcher,  # noqa: ARG001
    label_manager: LabelManager,  # noqa: ARG001
    loaded_config: BaseConfig,
    snmp_plugin_store: SNMPPluginStore,  # noqa: ARG001
    config_cache: ConfigCache,  # noqa: ARG001
    plugins: AgentBasedPlugins,  # noqa: ARG001
) -> tuple[MonitoringConfigBuilder, CoreClient]:
    match loaded_config.monitoring_core:
        case "nagios":
            from cmk.base.core.nagios import make_nagios_config_builder
            from cmk.base.core.nagios._create_config import NagiosCoreConfig

            return (
                make_nagios_config_builder(
                    paths.nagios_objects_file,
                    get_all_timeperiods(loaded_config.timeperiods),
                    NagiosCoreConfig.from_raw_config(loaded_config),
                ),
                NagiosClient(
                    objects_file=paths.nagios_objects_file,
                    init_script=paths.nagios_startscript,
                    config_file=paths.nagios_config_file,
                    binary_file=paths.nagios_binary,
                    cleanup_base=paths.omd_root,
                ),
            )
        case "cmc":
            raise RuntimeError("The Microcore is not available in this edition")
        case other_core:
            assert_never(other_core)
