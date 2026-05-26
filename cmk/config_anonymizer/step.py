#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import logging

from cmk.base.config import LoadingResult
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.config_anonymizer.interface import AnonInterface
from cmk.gui.config import Config
from cmk.utils.labels import Labels


class AnonymizeStep(abc.ABC):
    @abc.abstractmethod
    def run(
        self,
        anon_interface: AnonInterface,
        active_config: Config,
        loaded_config_result: LoadingResult,
        all_plugins: AgentBasedPlugins,
        builtin_host_labels: Labels,
        logger: logging.Logger,
    ) -> None:
        pass
