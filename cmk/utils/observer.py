#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from typing import Optional

from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostName

__all__ = [
    "ABCResourceObserver",
]


class ABCResourceObserver(abc.ABC):
    __slots__ = ['_logger', '_num_check_cycles', '_hostname']

    def __init__(self) -> None:
        super(ABCResourceObserver, self).__init__()
        self._logger = logging.getLogger("cmk.base")
        self._num_check_cycles = 0
        self._hostname = "<unknown>"

    @abc.abstractmethod
    def check_resources(self, hostname: Optional[HostName]) -> None:
        self._num_check_cycles += 1
        if hostname is not None:
            self._hostname = hostname

    def config_has_changed(self) -> None:
        pass

    def _warning(self, message: str) -> None:
        self._logger.warning('[cycle %d, host "%s"] %s', self._num_check_cycles, self._hostname,
                             message)

    def _costly_checks_enabled(self) -> bool:
        return self._logger.isEnabledFor(VERBOSE)

    def _verbose_output_enabled(self) -> bool:
        return self._logger.isEnabledFor(logging.DEBUG)
