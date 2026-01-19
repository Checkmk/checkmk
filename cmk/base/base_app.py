#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import Final

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.core.interface import MonitoringCore
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers import FetcherTriggerFactory, ProgramFetcher
from cmk.fetchers.snmp import SNMPPluginStore
from cmk.utils.labels import LabelManager, Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from .automations.automations import Automations
from .config import ConfigCache, LoadingResult, ObjectAttributes
from .modes.modes import Modes


class CheckmkBaseApp:
    """Provide features to the runtime

    Hold the features available to the runtime based on the context (edition) the app is created for.
    """

    def __init__(
        self,
        edition: Edition,
        modes: Modes,
        automations: Automations,
        make_bake_on_restart: Callable[[LoadingResult, Sequence[HostAddress]], Callable[[], None]],
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
        ],
        licensing_handler_type: type[LicensingHandler],
        make_fetcher_trigger: FetcherTriggerFactory,
        make_metric_backend_fetcher: Callable[
            [
                HostAddress,
                Callable[[HostAddress], ObjectAttributes],
                Callable[[HostAddress], float],
                bool,
            ],
            ProgramFetcher | None,
        ],
        get_builtin_host_labels: Callable[[SiteId], Labels],
    ) -> None:
        self.edition: Final = edition
        self.modes: Final = modes
        self.automations: Final = automations
        self.make_bake_on_restart: Final = make_bake_on_restart
        self.create_core: Final = create_core
        self.licensing_handler_type: Final = licensing_handler_type
        self.make_fetcher_trigger: Final = make_fetcher_trigger
        self.make_metric_backend_fetcher: Final = make_metric_backend_fetcher
        self.get_builtin_host_labels: Final = get_builtin_host_labels
