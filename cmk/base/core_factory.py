#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.base.config import ConfigCache
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.core.interface import MonitoringCore
from cmk.ccc.version import Edition, edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers.snmp import SNMPPluginStore
from cmk.utils import paths
from cmk.utils.labels import LabelManager
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.timeperiod import get_all_timeperiods


def get_licensing_handler_type() -> type[LicensingHandler]:
    if edition(paths.omd_root) is Edition.CRE:
        from cmk.utils.licensing.registry import get_available_licensing_handler_type
    else:
        from cmk.utils.cee.licensing.registry import (  # type: ignore[import,unused-ignore,no-redef]
            get_available_licensing_handler_type,
        )
    return get_available_licensing_handler_type()


# TODO: I think it would be much nicer if we had one version of this function
# for every edition, with the conditional imports at the callsites of this.
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
        case "cmc":
            from cmk.base.cee.precompute_timeperiods import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                precompute_timeperiods,
            )
            from cmk.base.configlib.cee.microcore import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                make_cmc_config,
                make_fetcher_config_writer,
                make_statehist_cache_config,
            )
            from cmk.base.core.cee.cmc import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                CmcPb,
                ConfigWriterInterface,
            )

            statehist_cache = make_statehist_cache_config(loaded_config)
            timeperiods = precompute_timeperiods(
                get_all_timeperiods(loaded_config.timeperiods),
                (statehist_cache.horizon if statehist_cache else 0),
                loaded_config.cmc_timeperiod_horizon,
            )
            helper_config_writers: list[ConfigWriterInterface] = [
                make_fetcher_config_writer(
                    edition,
                    loaded_config,
                    label_manager.labels_of_host,
                    config_cache,
                    plugins,
                    snmp_plugin_store,
                )
            ]

            if edition in (Edition.CCE, Edition.CME, Edition.CSE):
                from cmk.base.configlib.cce.relay import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                    make_relay_config_writers,
                )

                helper_config_writers.extend(
                    make_relay_config_writers(
                        loaded_config,
                        matcher,
                        config_cache,
                        label_manager,
                        plugins,
                        snmp_plugin_store,
                        timeperiods,
                    )
                )

            return CmcPb(  # type: ignore[no-any-return, unused-ignore]
                get_licensing_handler_type(),
                make_cmc_config(
                    loaded_config, matcher, label_manager, statehist_cache, timeperiods
                ),
                helper_config_writers,
            )
        case "nagios":
            from cmk.base.core.nagios import NagiosCore

            return NagiosCore(
                get_licensing_handler_type(),
                paths.nagios_startscript,
                paths.nagios_objects_file,
                get_all_timeperiods(loaded_config.timeperiods),
            )
        case other_core:
            assert_never(other_core)
