#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import sys
from typing import Dict, Final, Optional

import cmk.utils.misc
import cmk.utils.render as render
from cmk.utils.caching import config_cache, runtime_cache
from cmk.utils.log import VERBOSE

__all__ = [
    "ABCResourceObserver",
    "AbstractMemoryObserver",
    "FetcherMemoryObserver",
]


class ABCResourceObserver(abc.ABC):
    __slots__ = ["_logger", "_num_check_cycles", "_hint"]

    def __init__(self) -> None:
        super().__init__()
        self._logger = logging.getLogger("cmk.base")
        self._num_check_cycles = 0
        self._hint = "<unknown>"

    def _register_check(self, hint: Optional[str]) -> None:
        self._num_check_cycles += 1
        if hint is not None:
            self._hint = hint

    @abc.abstractmethod
    def check_resources(self, hint: Optional[str]) -> None:
        """hint should provide reasonable additional information useful for analysis.
        Good examples are hostname, service name or raw command."""
        raise NotImplementedError()

    def config_has_changed(self) -> None:
        pass

    def _context(self) -> str:
        return f'[cycle {self._num_check_cycles}, host "{self._hint}"]'

    def _warning(self, message: str) -> None:
        self._logger.warning("%s %s", self._context(), message)

    def _error(self, message: str) -> None:
        self._logger.error("%s %s", self._context(), message)

    def _costly_checks_enabled(self) -> bool:
        return self._logger.isEnabledFor(VERBOSE)

    def _verbose_output_enabled(self) -> bool:
        return self._logger.isEnabledFor(logging.DEBUG)


class AbstractMemoryObserver(ABCResourceObserver):
    """Observes usage of the memory by the current process. Excessive memory usage by
    process is defined as (initial VM size)*self._allowed_growth/100.
    Initial VM size is stored at 5-th call of check_resources().
    """

    __slots__ = ["_memory_usage", "_allowed_growth", "_steady_cycle_num"]

    def __init__(self, allowed_growth: int) -> None:
        """allowed_growth is the permitted increase of the VM size measured in percents."""
        super().__init__()
        self._memory_usage = 0
        self._allowed_growth = allowed_growth
        self._steady_cycle_num: Final = 5

    def memory_usage(self) -> int:
        return self._memory_usage

    def memory_allowed(self) -> int:
        return int(self._allowed_growth / 100 * self._memory_usage)

    def _validate_size(self) -> bool:
        """Determines whether RAM limit was exceeded.
        Registers (once) memory status when steady state is achieved.
        """

        # We should have reached a steady state after 5 check cycles.
        if self._num_check_cycles < self._steady_cycle_num:
            return True

        # We observe every cycle after reaching the steady state.
        # This is OK performance-wise: ~7 microseconds per observation.
        new_memory_usage = self._vm_size()
        if self._num_check_cycles == self._steady_cycle_num:
            self._print_global_memory_usage()
            self._memory_usage = new_memory_usage
            return True

        return new_memory_usage <= self.memory_allowed()

    @staticmethod
    def _vm_size() -> int:
        with open("/proc/self/statm") as f:  # see: man proc(5).
            return int(f.read().split()[0]) * 4096

    def _print_global_memory_usage(self) -> None:
        if not self._verbose_output_enabled():
            return
        globals_sizes = {
            varname: cmk.utils.misc.total_size(value) for (varname, value) in globals().items()
        }
        self._dump("APPROXIMATE SIZES: GLOBALS TOP 50", globals_sizes, 50)
        for title, module in [
            ("CONFIG CACHE", config_cache),
            ("RUNTIME CACHE", runtime_cache),
        ]:
            self._dump("APPROXIMATE SIZES: %s" % title, module.dump_sizes(), None)

    def _dump(self, header: str, sizes: Dict[str, int], limit: Optional[int]) -> None:
        self._warning("=== %s ====" % header)
        for varname, size_bytes in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:limit]:
            self._warning("%10s %s" % (render.fmt_bytes(size_bytes), varname))


class FetcherMemoryObserver(AbstractMemoryObserver):
    """Controls usage of the memory by the Fetcher.
    Call sys.exit(14) if during call of check_resources() memory is overloaded.
    The microcore is responsible for restart of Fetcher.
    """

    def _context(self) -> str:
        return f'[cycle {self._num_check_cycles}, command "{self._hint}"]'

    def check_resources(self, hint: Optional[str]) -> None:
        self._register_check(hint)

        if not self._validate_size():
            self._error(
                "memory usage increased from %s to %s, exiting"
                % (
                    render.fmt_bytes(self.memory_usage()),
                    render.fmt_bytes(self._vm_size()),
                )
            )
            sys.exit(14)
