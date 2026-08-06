#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.core.interface import MonitoringCore
from cmk.ccc.version import Edition
from cmk.checkengine.fetcher_utils.trigger import FetcherTriggerFactory
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.snmplib import SNMPPluginStore
from cmk.licensing.handler import LicensingHandler
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher

from .config import ConfigCache


@dataclass(frozen=True, kw_only=True)
class CheckmkBaseApp:
    """Provide features to the runtime

    Hold the features available to the runtime based on the context (edition) the app is created for.
    """

    edition: Edition
    create_core: Callable[
        [
            Edition,
            RulesetMatcher,
            LabelManager,
            BaseConfig,
            SNMPPluginStore,
            ConfigCache,
            AgentBasedPlugins,
        ],
        MonitoringCore,
    ]
    licensing_handler_factory: Callable[[], LicensingHandler]
    make_fetcher_trigger: FetcherTriggerFactory
