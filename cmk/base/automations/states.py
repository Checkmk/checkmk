#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk import trace
from cmk.automations.internal import AutomationState
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.base_app import CheckmkBaseApp

tracer = trace.get_tracer()


class BaseConfigState(AutomationState):
    """The state of an automation that needs the base configuration only.

    It picks the configuration values from the raw configuration, and derives
    nothing below them: no hosts, no rulesets, no caches.
    """

    def __init__(self, _omd_root: Path, raw_config: Mapping[str, object]) -> None:
        self.loaded_config = config.make_base_config(raw_config)

    @override
    def update(self, _omd_root: Path, raw_config: Mapping[str, object]) -> None:
        self.loaded_config = config.make_base_config(raw_config)


class CommonState(AutomationState):
    """The state most automations share for now.

    It derives what the handlers used to get passed from the raw configuration.
    The automations that need it name this class as their factory, so the engine
    builds it once. They will move to states of their own, one by one.
    """

    def __init__(self, omd_root: Path, raw_config: Mapping[str, object]) -> None:
        self.app: CheckmkBaseApp = make_app(omd_root)
        self.loading_result = _derive_loading_result(raw_config)

    @override
    def update(self, omd_root: Path, raw_config: Mapping[str, object]) -> None:
        # The site, and with it the app, does not change while we run. We rebuild the
        # app anyway, so that the state is derived from its arguments alone.
        self.app = make_app(omd_root)
        # Deriving afresh also resets all caches below the configuration, including
        # those of the ruleset optimizer: a new configuration starts from scratch.
        self.loading_result = _derive_loading_result(raw_config)


def _derive_loading_result(raw_config: Mapping[str, object]) -> config.LoadingResult:
    with tracer.span("derive_loading_result"):
        return config.perform_post_config_loading_actions(
            raw_config,
            autochecks_dir=cmk.utils.paths.autochecks_dir,
            discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
            builtin_host_labels_file=cmk.utils.paths.builtin_host_labels_file,
        )
