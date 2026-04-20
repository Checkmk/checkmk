#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.core.interface import MonitoringCore
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers import Fetcher, FetcherTriggerFactory
from cmk.helper_interface import AgentRawData
from cmk.licensing.handler import LicensingHandler
from cmk.snmplib import SNMPPluginStore
from cmk.utils.labels import LabelManager, Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from .automations.automations import Automations
from .config import ConfigCache, LoadingResult, ObjectAttributes
from .modes.modes import Modes


@dataclass(frozen=True)
class CheckmkBaseApp:
    """Provide features to the runtime

    Hold the features available to the runtime based on the context (edition) the app is created for.
    """

    edition: Edition
    modes: Modes
    automations: Automations
    make_bake_on_restart: Callable[[LoadingResult, Sequence[HostAddress]], Callable[[], None]]
    create_core: Callable[
        [
            Edition,
            RulesetMatcher,
            LabelManager,
            LoadedConfigFragment,
            SNMPPluginStore,
            ConfigCache,
            AgentBasedPlugins,
        ],
        MonitoringCore,
    ]
    licensing_handler_factory: Callable[[], LicensingHandler]
    make_fetcher_trigger: FetcherTriggerFactory
    make_metric_backend_fetcher: Callable[
        [
            HostAddress,
            Callable[[HostAddress], ObjectAttributes],
            Callable[[HostAddress], float],
        ],
        Fetcher[AgentRawData] | None,
    ]
    get_builtin_host_labels: Callable[[SiteId], Labels]
    core_performance_settings: Callable[[LoadedConfigFragment], Mapping[str, int]]
