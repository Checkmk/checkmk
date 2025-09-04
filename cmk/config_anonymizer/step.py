#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import logging

from cmk.config_anonymizer.interface import AnonInterface
from cmk.gui.config import Config


class AnonymizeStep(abc.ABC):
    @abc.abstractmethod
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        pass
